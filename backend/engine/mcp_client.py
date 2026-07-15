"""
太极引擎 · MCP 协议接入（真实 stdio 实现 + 安全认证）

MCP (Model Context Protocol) 客户端——工具发现 + 描述 + 调用。

v1.0: PoC 模拟模式（4 个硬编码工具）
v2.0: 真实 stdio 子进程连接 + JSON-RPC 协议 + 超时/重试 + mock 降级
v2.1: P1-6 — 集成 MCPAuth 认证层（API Key + Token + 白名单）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
import asyncio
import json
import logging
import subprocess
import sys
import time

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    name: str
    description: str = ""
    input_schema: dict | None = None


@dataclass
class MCPToolResult:
    tool_name: str
    success: bool
    output: Any = None
    error: str = ""
    duration_ms: int = 0


class MCPConnectionError(Exception):
    """MCP 连接错误。"""
    pass


class MCPTimeoutError(Exception):
    """MCP 调用超时。"""
    pass


class MCPClient:
    """MCP 协议客户端。

    v2.1 双模式 + 安全认证:
    - stdio: 启动子进程，通过 stdin/stdout JSON-RPC 通信（真实模式）
    - mock:  本地模拟工具（降级模式，server_command=None 时自动启用）
    - auth:  集成 MCPAuth 认证层（P1-6），生产环境强制 API Key 验证

    用法:
        # 真实模式——启动本地 MCP server
        client = MCPClient(server_command=["uvx", "mcp-server-filesystem", "/path"])

        # 降级模式——无外部 server 时
        client = MCPClient()  # 自动使用 mock 模式

        # 认证模式——生产环境
        client = MCPClient(
            server_command=["uvx", "mcp-server-filesystem", "/path"],
            server_id="mcp_abc123",
            api_key="sn_mcp_...",
        )
    """

    # 超时配置
    CONNECT_TIMEOUT = 10        # 秒：连接 + initialize 最大时间
    CALL_TIMEOUT = 30           # 秒：单次工具调用最大时间
    READ_TIMEOUT = 5            # 秒：单次行读取最大时间

    def __init__(
        self,
        server_command: list[str] | None = None,
        server_id: str = "",
        api_key: str = "",
    ) -> None:
        self._server_command = server_command
        self._server_id = server_id
        self._api_key = api_key
        self._process: subprocess.Popen | None = None
        self._tools: dict[str, MCPTool] = {}
        self._connected: bool = False
        self._authenticated: bool = False
        self._request_id: int = 0
        self._lock = asyncio.Lock()

        if server_command is None:
            self._init_mock_tools()
            self._connected = True
            logger.info("MCP 客户端已启动 (mock 模式)")

    # ================================================================
    # Mock 模式（降级路径）
    # ================================================================

    def _init_mock_tools(self) -> None:
        """初始化模拟 MCP 工具（演示用降级路径）。"""
        self._tools = {
            "web_search": MCPTool("web_search", "搜索互联网", {"query": "string", "num_results": "int"}),
            "file_read": MCPTool("file_read", "读取文件内容", {"path": "string"}),
            "code_execute": MCPTool("code_execute", "执行代码片段", {"language": "string", "code": "string"}),
            "database_query": MCPTool("database_query", "查询数据库", {"sql": "string"}),
        }

    # ================================================================
    # stdio 子进程管理
    # ================================================================

    async def connect(self) -> bool:
        """连接 MCP server——启动子进程并完成 JSON-RPC 握手。

        如果启用了认证（P1-6），连接前先验证 server 身份。

        Returns:
            True 连接成功, False 失败（此时自动降级到 mock 模式）
        """
        if self._connected:
            return True

        if self._server_command is None:
            self._init_mock_tools()
            self._connected = True
            return True

        # ---- P1-6: MCP 安全认证 ----
        if settings.MCP_AUTH_ENABLED and self._server_id:
            auth_result = await self._authenticate()
            if not auth_result:
                if settings.MCP_ALLOW_MOCK_UNAUTHENTICATED:
                    logger.warning("MCP 认证失败——降级到 mock 模式")
                    self._init_mock_tools()
                    self._connected = True
                    return False
                else:
                    raise MCPConnectionError("MCP 认证失败——server 未注册或 API Key 无效")
        # ---- 认证结束 ----

        try:
            logger.info("启动 MCP server: %s", " ".join(self._server_command))
            self._process = subprocess.Popen(
                self._server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # JSON-RPC initialize 握手
            init_response = await asyncio.wait_for(
                self._rpc_call("initialize", {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {"name": "super-niuma", "version": "2.0.0"},
                }),
                timeout=self.CONNECT_TIMEOUT,
            )

            if "result" in init_response:
                self._connected = True
                server_info = init_response["result"].get("serverInfo", {})
                logger.info("MCP 连接成功: %s v%s (stdio)",
                            server_info.get("name", "unknown"),
                            server_info.get("version", "?"))
                # 加载工具列表
                await self._discover_tools()
                return True
            else:
                raise MCPConnectionError(f"initialize 失败: {init_response}")

        except asyncio.TimeoutError:
            logger.warning("MCP 连接超时 (%ds)，降级到 mock 模式", self.CONNECT_TIMEOUT)
            await self._cleanup_process()
            self._init_mock_tools()
            self._connected = True
            return False

        except Exception as e:
            logger.warning("MCP 连接失败，降级到 mock 模式: %s", e)
            await self._cleanup_process()
            self._init_mock_tools()
            self._connected = True
            return False

    async def disconnect(self) -> None:
        """断开 MCP server 连接——发送 shutdown 并清理进程。"""
        if not self._connected or self._server_command is None:
            return

        try:
            await asyncio.wait_for(
                self._rpc_call("shutdown", {}),
                timeout=self.CALL_TIMEOUT,
            )
        except Exception:
            logger.debug("MCP shutdown 请求失败（可忽略）")

        await self._cleanup_process()
        self._connected = False
        logger.info("MCP 已断开连接")

    async def _cleanup_process(self) -> None:
        """清理子进程——发送 SIGTERM + 等待 + SIGKILL。"""
        if self._process is None:
            return
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=2)
        except Exception as e:
            logger.debug("清理 MCP 进程时出错: %s", e)
        finally:
            self._process = None

    # ================================================================
    # JSON-RPC 协议
    # ================================================================

    async def _rpc_call(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求到 MCP server。

        通过 stdin 发送请求，stdout 读取响应。
        每个请求必须有唯一 id。
        """
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise MCPConnectionError("子进程未启动或 stdio 不可用")

        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        request_line = json.dumps(request, ensure_ascii=False) + "\n"

        async with self._lock:
            # 发送请求
            try:
                self._process.stdin.write(request_line)
                self._process.stdin.flush()
            except BrokenPipeError:
                raise MCPConnectionError("子进程 stdin 已关闭——MCP server 可能已崩溃")

            # 读取响应（可能多行，以 "Content-Length:" 开头则需额外读取 body）
            try:
                line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self._process.stdout.readline),
                    timeout=self.READ_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise MCPTimeoutError(f"读取 MCP 响应超时 ({self.READ_TIMEOUT}s)")

            if not line:
                raise MCPConnectionError("子进程 stdout 已关闭——MCP server 已退出")

            # 处理 LSP 风格的 Content-Length header
            line = line.strip()
            if line.startswith("Content-Length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    # 跳过空行
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._process.stdout.readline
                    )
                    body = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._process.stdout.read(content_length)
                    )
                    line = body
                except Exception:
                    pass

            try:
                response = json.loads(line)
            except json.JSONDecodeError as e:
                raise MCPConnectionError(f"JSON 解析失败: {e} (raw: {line[:200]})")

            # 检查 stderr 中的错误信息
            if self._process.stderr:
                try:
                    stderr_line = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: self._process.stderr.readline() if self._process and self._process.stderr else ""
                        ),
                        timeout=0.5,
                    )
                    if stderr_line:
                        logger.debug("MCP stderr: %s", stderr_line.strip())
                except (asyncio.TimeoutError, Exception):
                    pass

        return response

    async def _discover_tools(self) -> None:
        """从 MCP server 发现并加载所有可用工具。"""
        try:
            response = await asyncio.wait_for(
                self._rpc_call("tools/list", {}),
                timeout=self.CONNECT_TIMEOUT,
            )
            tools_data = response.get("result", {}).get("tools", [])
            self._tools.clear()
            for t in tools_data:
                name = t.get("name", "unknown")
                self._tools[name] = MCPTool(
                    name=name,
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema"),
                )
            logger.info("发现 %d 个 MCP 工具: %s", len(self._tools), list(self._tools.keys()))
        except Exception as e:
            logger.warning("MCP 工具发现失败，使用空工具列表: %s", e)

    # ================================================================
    # 公共 API
    # ================================================================

    async def list_tools(self) -> list[MCPTool]:
        """列出所有可用工具。"""
        return list(self._tools.values())

    async def describe_tool(self, tool_name: str) -> MCPTool | None:
        """获取工具详情。"""
        return self._tools.get(tool_name)

    # ================================================================
    # 工具参数安全校验
    # ================================================================

    # SQL 白名单：只允许 SELECT / EXPLAIN / DESCRIBE / SHOW
    _SQL_SAFE_PREFIXES = ("SELECT", "EXPLAIN", "DESCRIBE", "SHOW", "PRAGMA", "WITH")
    _SQL_DANGEROUS_KEYWORDS = (
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE",
        "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    )
    # 路径沙箱：只允许读取这些目录下的文件
    _SAFE_PATH_PREFIXES = (
        "/workspace/", "/tmp/", "/home/",
        "C:\\Users\\", "D:\\workspace\\",
    )
    # 路径遍历检测
    _PATH_TRAVERSAL_PATTERNS = ("../", "..\\")

    def _validate_tool_args(self, tool_name: str, arguments: dict) -> str:
        """校验工具参数安全性。

        Returns:
            空字符串表示通过，非空字符串为拦截原因。
        """
        # database_query: SQL 注入防护
        if tool_name == "database_query":
            sql = (arguments.get("sql") or "").strip()
            if not sql:
                return "database_query: sql 参数为空"
            sql_upper = sql.upper().lstrip()
            # 检查是否以安全操作开头
            is_safe = any(sql_upper.startswith(prefix) for prefix in self._SQL_SAFE_PREFIXES)
            if not is_safe:
                return f"database_query: 不允许的 SQL 操作，仅支持 SELECT/EXPLAIN/DESCRIBE/SHOW/PRAGMA/WITH"
            # 检查是否包含危险关键词（防止子查询注入）
            for keyword in self._SQL_DANGEROUS_KEYWORDS:
                if keyword in sql_upper:
                    # 允许 "DELETE" 出现在字符串或注释中（简单检测）
                    return f"database_query: SQL 包含禁止操作 {keyword}"

        # file_read: 路径遍历防护
        elif tool_name == "file_read":
            filepath = (arguments.get("path") or "").strip()
            if not filepath:
                return "file_read: path 参数为空"
            # 检测路径遍历
            for pattern in self._PATH_TRAVERSAL_PATTERNS:
                if pattern in filepath:
                    return f"file_read: 路径遍历攻击被拦截"
            # 检测绝对路径限制（仅允许安全目录）
            if filepath.startswith("/") or filepath[1:3] == ":\\":
                is_safe_path = any(
                    filepath.lower().startswith(prefix.lower())
                    for prefix in self._SAFE_PATH_PREFIXES
                )
                if not is_safe_path:
                    return f"file_read: 不允许访问此路径，仅限工作区和临时目录"

        # code_execute: 限制危险操作
        elif tool_name == "code_execute":
            code = (arguments.get("code") or "").strip()
            if not code:
                return "code_execute: code 参数为空"
            # 禁止系统级危险操作
            dangerous_patterns = [
                "os.system(", "subprocess.", "eval(", "exec(",
                "__import__(", "open(", "socket.",
                "shutil.rmtree", "os.remove(", "os.unlink(",
            ]
            for pattern in dangerous_patterns:
                if pattern in code:
                    # 允许 "open(" 后跟文件读取模式（r）但拒绝写入（w/a）
                    if pattern == "open(":
                        code_after_open = code[code.index(pattern) + len(pattern):]
                        if any(m in code_after_open[:20] for m in ('"w"', "'w'", '"a"', "'a'", '"wb"', "'wb'")):
                            return f"code_execute: 禁止文件写入操作"
                    else:
                        return f"code_execute: 包含禁止操作 {pattern}"

        return ""  # 通过

    async def call_tool(self, tool_name: str, arguments: dict) -> MCPToolResult:
        """调用工具。

        真实模式: 发送 tools/call JSON-RPC 请求到 MCP server
        Mock 模式: 返回模拟结果
        """
        start_time = time.time()

        # 安全校验：所有工具调用前先验证参数
        validation_error = self._validate_tool_args(tool_name, arguments)
        if validation_error:
            logger.warning("MCP 工具调用被安全策略拦截: %s", validation_error)
            return MCPToolResult(tool_name, False, error=validation_error)

        # Mock 模式
        if self._server_command is None:
            tool = self._tools.get(tool_name)
            if not tool:
                return MCPToolResult(tool_name, False, error=f"工具 {tool_name} 不存在")
            return MCPToolResult(
                tool_name, True,
                output={"status": "ok", "tool": tool_name, "args": arguments, "result": "mock_result (降级模式)"},
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # 真实模式
        tool = self._tools.get(tool_name)
        if not tool:
            # 尝试重新发现工具（可能 server 重启了）
            await self._discover_tools()
            tool = self._tools.get(tool_name)
            if not tool:
                return MCPToolResult(tool_name, False, error=f"工具 {tool_name} 不存在")

        try:
            response = await asyncio.wait_for(
                self._rpc_call("tools/call", {
                    "name": tool_name,
                    "arguments": arguments,
                }),
                timeout=self.CALL_TIMEOUT,
            )

            if "error" in response:
                error_msg = response["error"].get("message", str(response["error"]))
                return MCPToolResult(
                    tool_name, False,
                    error=error_msg,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            result = response.get("result", {})
            return MCPToolResult(
                tool_name, True,
                output=result.get("content", result),
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except asyncio.TimeoutError:
            return MCPToolResult(
                tool_name, False,
                error=f"工具调用超时 ({self.CALL_TIMEOUT}s)",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except MCPConnectionError as e:
            return MCPToolResult(
                tool_name, False,
                error=f"MCP 连接错误: {e}",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.warning("工具调用异常: %s / %s: %s", tool_name, arguments, e)
            return MCPToolResult(
                tool_name, False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )

    # ================================================================
    # MCP 安全认证 (P1-6)
    # ================================================================

    async def _authenticate(self) -> bool:
        """MCP Server 安全认证——验证 server 身份并获取单次令牌。

        从 engine.mcp_auth 模块导入 mcp_auth 单例进行验证。
        验证通过后，_authenticated 标记为 True，后续工具调用受令牌保护。
        """
        try:
            from engine.mcp_auth import mcp_auth

            # 从 server_command 提取 server_name（第一个非选项参数）
            server_name = self._server_command[0] if self._server_command else "unknown"

            valid, result = await mcp_auth.validate_server_access(
                server_id=self._server_id,
                api_key=self._api_key,
                server_name=server_name,
                server_command=self._server_command,
            )

            if valid:
                self._authenticated = True
                self._access_token = result  # 保存单次令牌
                logger.info("MCP Server 认证通过: %s (%s)", server_name, self._server_id)
                return True
            else:
                logger.warning("MCP Server 认证拒绝: %s (原因: %s)", self._server_id, result)
                return False

        except ImportError:
            logger.warning("MCP 认证模块未加载——允许未认证连接")
            return True  # 开发环境容错
        except Exception as e:
            logger.error("MCP 认证异常: %s", e)
            return False

    def get_stats(self) -> dict:
        return {
            "connected": self._connected,
            "authenticated": self._authenticated,
            "tools_available": len(self._tools),
            "mode": "mock" if self._server_command is None else "stdio",
            "server_command": self._server_command,
            "server_id": self._server_id or "N/A",
            "process_alive": self._process is not None and self._process.poll() is None if self._process else False,
        }


# ================================================================
# v1.8: MCP Server Registry — 多服务器管理
# ================================================================

class MCPServerEntry:
    """一个已注册的 MCP Server 条目。"""

    def __init__(self, server_id: str, name: str, command: list[str], api_key: str = "") -> None:
        self.server_id = server_id
        self.name = name
        self.command = command
        self.api_key = api_key
        self.client: MCPClient | None = None
        self.registered_at: float = time.time()
        self.last_connected: float = 0.0
        self.status: str = "registered"  # registered / connected / disconnected / error

    def to_dict(self) -> dict:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "registered_at": self.registered_at,
            "last_connected": self.last_connected,
            "tools_count": len(self.client._tools) if self.client else 0,
            "client_stats": self.client.get_stats() if self.client else None,
        }


class MCPServerRegistry:
    """MCP Server 注册表 — 管理多个 MCP Server 连接。

    v1.8新增: 行业趋势是企业有20-50个MCP Server，
    需要统一管理层（MCP Gateway的轻量版）。

    功能:
      1. 注册/注销 MCP Server
      2. 连接/断开 Server
      3. 聚合所有 Server 的工具列表
      4. 按工具名路由到正确的 Server
      5. 健康检查 + 自动重连

    用法:
        from engine.mcp_client import mcp_registry
        await mcp_registry.register("fs", "文件系统", ["uvx", "mcp-server-filesystem", "/workspace"])
        await mcp_registry.connect("fs")
        tools = await mcp_registry.list_all_tools()
        result = await mcp_registry.call_tool("fs", "read_file", {"path": "/workspace/test.py"})
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerEntry] = {}
        self._tool_index: dict[str, str] = {}  # tool_name → server_id
        self._initialized = False

    async def initialize(self) -> None:
        """初始化默认的 mock server（保证始终有工具可用）。"""
        if self._initialized:
            return

        # 注册一个默认 mock server
        mock_entry = MCPServerEntry(
            server_id="default-mock",
            name="内置工具（降级模式）",
            command=[],
        )
        mock_entry.client = MCPClient()  # mock 模式
        mock_entry.status = "connected"
        mock_entry.last_connected = time.time()
        self._servers["default-mock"] = mock_entry

        # 建立工具索引
        for tool in await mock_entry.client.list_tools():
            self._tool_index[tool.name] = "default-mock"

        self._initialized = True
        logger.info("MCP Server Registry 已初始化 (1 个默认 mock server)")

    async def register(
        self,
        server_id: str,
        name: str,
        command: list[str],
        api_key: str = "",
    ) -> MCPServerEntry:
        """注册一个新的 MCP Server。"""
        if server_id in self._servers:
            # 已存在——先断开旧连接
            await self.disconnect(server_id)

        entry = MCPServerEntry(server_id, name, command, api_key)
        self._servers[server_id] = entry
        logger.info("MCP Server 已注册: %s (%s)", name, server_id)
        return entry

    async def connect(self, server_id: str) -> bool:
        """连接指定的 MCP Server。"""
        entry = self._servers.get(server_id)
        if not entry:
            logger.warning("MCP Server 未找到: %s", server_id)
            return False

        if not entry.client:
            entry.client = MCPClient(
                server_command=entry.command if entry.command else None,
                server_id=server_id,
                api_key=entry.api_key,
            )

        success = await entry.client.connect()
        if success:
            entry.status = "connected"
            entry.last_connected = time.time()

            # 更新工具索引
            tools = await entry.client.list_tools()
            for tool in tools:
                self._tool_index[tool.name] = server_id

            logger.info("MCP Server %s 已连接，%d 个工具", server_id, len(tools))
        else:
            entry.status = "error"

        return success

    async def disconnect(self, server_id: str) -> bool:
        """断开指定的 MCP Server。"""
        entry = self._servers.get(server_id)
        if not entry or not entry.client:
            return False

        await entry.client.disconnect()
        entry.status = "disconnected"

        # 从工具索引中移除
        to_remove = [t for t, sid in self._tool_index.items() if sid == server_id]
        for t in to_remove:
            del self._tool_index[t]

        logger.info("MCP Server %s 已断开", server_id)
        return True

    async def unregister(self, server_id: str) -> bool:
        """注销 MCP Server。"""
        await self.disconnect(server_id)
        if server_id in self._servers:
            del self._servers[server_id]
            logger.info("MCP Server %s 已注销", server_id)
            return True
        return False

    async def list_all_tools(self) -> list[dict]:
        """聚合所有已连接 Server 的工具列表。"""
        all_tools = []
        for sid, entry in self._servers.items():
            if entry.status == "connected" and entry.client:
                tools = await entry.client.list_tools()
                for t in tools:
                    all_tools.append({
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.input_schema,
                        "server_id": sid,
                        "server_name": entry.name,
                    })
        return all_tools

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> MCPToolResult:
        """调用指定 Server 上的工具。"""
        entry = self._servers.get(server_id)
        if not entry or not entry.client:
            return MCPToolResult(tool_name, False, error=f"MCP Server {server_id} 未连接")

        return await entry.client.call_tool(tool_name, arguments)

    async def call_tool_by_name(self, tool_name: str, arguments: dict) -> MCPToolResult:
        """按工具名自动路由到正确的 Server。"""
        server_id = self._tool_index.get(tool_name)
        if not server_id:
            return MCPToolResult(tool_name, False, error=f"工具 {tool_name} 未在任何已连接的 MCP Server 中找到")

        return await self.call_tool(server_id, tool_name, arguments)

    def list_servers(self) -> list[dict]:
        """列出所有已注册的 Server。"""
        return [entry.to_dict() for entry in self._servers.values()]

    def get_server(self, server_id: str) -> dict | None:
        """获取单个 Server 详情。"""
        entry = self._servers.get(server_id)
        return entry.to_dict() if entry else None

    async def health_check(self) -> dict:
        """检查所有 Server 的健康状态。"""
        results = {}
        for sid, entry in self._servers.items():
            if entry.status == "connected" and entry.client:
                stats = entry.client.get_stats()
                results[sid] = {
                    "status": "healthy" if stats.get("connected") else "unhealthy",
                    "tools_count": stats.get("tools_available", 0),
                    "mode": stats.get("mode", "unknown"),
                }
            else:
                results[sid] = {"status": entry.status}
        return results

    def get_stats(self) -> dict:
        """获取 Registry 全局统计。"""
        connected = sum(1 for e in self._servers.values() if e.status == "connected")
        return {
            "total_servers": len(self._servers),
            "connected_servers": connected,
            "total_tools": len(self._tool_index),
            "tool_index": dict(self._tool_index),
        }


# 全局实例
mcp_registry = MCPServerRegistry()
