"""
太极引擎 · 自我进化写入器（Self-Evolution Writer）

ClosureEngine 生成变更建议 → SelfEvolutionWriter 执行写入——
备份 → 修改配置 → 验证 → 失败回滚。

不做"自己写 Python 逻辑"（v2.0）——只做"自己调参数"（v1.6）。
配置类变更：阈值、权重、预算。这些是安全的，不需要 AST 级别的代码修改。
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable
import json
import os
import shutil


@dataclass
class EvolutionCheckpoint:
    """变更前的完整状态快照。用于回滚。"""
    id: str
    timestamp: str
    module_name: str
    old_value: dict
    file_backup_path: str = ""
    verified: bool = False


class SelfEvolutionWriter:
    """自我进化写入器——只修改安全的配置类数据。

    工作流：
      1. 备份当前状态
      2. 应用变更
      3. 验证——跑一轮健康检查
      4. 通过 → 保留；失败 → 自动回滚
    """

    BACKUP_DIR = "data/evolution_backups"

    def __init__(self, backup_dir: str | None = None) -> None:
        self._backup_dir = backup_dir or self.BACKUP_DIR
        self._checkpoints: list[EvolutionCheckpoint] = []
        self._applied: list[EvolutionCheckpoint] = []
        self._rolled_back: list[EvolutionCheckpoint] = []

    def backup(self, module_name: str, current_state: dict) -> EvolutionCheckpoint:
        """备份当前状态。"""
        os.makedirs(self._backup_dir, exist_ok=True)
        cp_id = f"evolve-{datetime.now().strftime('%Y%m%d%H%M%S')}-{module_name}"
        cp = EvolutionCheckpoint(
            id=cp_id,
            timestamp=datetime.now().isoformat(),
            module_name=module_name,
            old_value=dict(current_state),
        )

        # 写备份文件
        backup_path = os.path.join(self._backup_dir, f"{cp_id}.json")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(current_state, f, ensure_ascii=False, indent=2)
        cp.file_backup_path = backup_path

        self._checkpoints.append(cp)
        return cp

    def apply(self, checkpoint: EvolutionCheckpoint,
              apply_fn: Callable, verify_fn: Callable | None = None) -> bool:
        """应用变更 + 验证 + 失败自动回滚。

        返回 True = 成功应用，False = 已回滚。
        """
        try:
            apply_fn()
        except Exception as e:
            self._rollback(checkpoint)
            return False

        # 验证
        if verify_fn:
            try:
                verified = verify_fn()
                if not verified:
                    self._rollback(checkpoint)
                    return False
            except Exception:
                self._rollback(checkpoint)
                return False

        checkpoint.verified = True
        self._applied.append(checkpoint)
        return True

    def _rollback(self, checkpoint: EvolutionCheckpoint) -> None:
        """回滚到备份状态——从备份文件恢复原始配置。"""
        import logging
        logger = logging.getLogger("niuma.evolution")

        if checkpoint.file_backup_path and os.path.exists(checkpoint.file_backup_path):
            try:
                with open(checkpoint.file_backup_path, "r", encoding="utf-8") as f:
                    restored_state = json.load(f)
                # 恢复：将备份数据写回原位置
                # 对于 budget 类变更——恢复 token_budget
                if checkpoint.module_name.startswith("budget:"):
                    agent_id = checkpoint.module_name.split(":", 1)[1]
                    from engine.token_budget import token_budget
                    old_budget = restored_state.get("budget", 200000)
                    token_budget.set_agent_budget(agent_id, old_budget)
                    logger.info(f"已回滚 {agent_id} 预算至 {old_budget}")
                # 对于 weight 类变更——写入 weights 文件
                elif checkpoint.module_name.startswith("weight:"):
                    weight_file = os.path.join(self._backup_dir, "..", "model_weights.json")
                    with open(weight_file, "w", encoding="utf-8") as wf:
                        json.dump(restored_state, wf, ensure_ascii=False, indent=2)
                    logger.info(f"已回滚权重配置: {checkpoint.module_name}")
                else:
                    logger.warning(f"未知回滚类型: {checkpoint.module_name}，备份已保留在 {checkpoint.file_backup_path}")
            except Exception as e:
                logger.exception(f"回滚失败，备份文件: {checkpoint.file_backup_path}")
        else:
            logger.warning(f"无可用的回滚备份: {checkpoint.id}")

        self._rolled_back.append(checkpoint)

    def auto_evolve_budget(self, agent_id: str, new_budget: int,
                           current_state_fn: Callable,
                           apply_fn: Callable,
                           verify_fn: Callable) -> tuple[bool, str]:
        """自动进化——调整 Agent Token 预算。

        这是最安全的自进化操作。ClosureEngine 发现某 Agent 类型高成功率 → 自动提预算。
        """
        cp = self.backup(f"budget:{agent_id}", {"agent_id": agent_id, "budget": new_budget})
        success = self.apply(cp, apply_fn, verify_fn)
        if success:
            return True, f"自动提升 {agent_id} 预算到 {new_budget}"
        else:
            return False, f"{agent_id} 预算调整失败，已自动回滚"

    def auto_evolve_model_weight(self, model_name: str, task_type: str, new_weight: float,
                                  apply_fn: Callable) -> tuple[bool, str]:
        """自动进化——调整模型权重。

        高成功率任务类型的模型组合自动提升权重。
        """
        cp = self.backup(f"weight:{model_name}:{task_type}", {
            "model": model_name, "task_type": task_type, "weight": new_weight,
        })
        success = self.apply(cp, apply_fn)
        if success:
            return True, f"自动提升 {model_name}+{task_type} 权重"
        return False, "权重调整失败，已回滚"

    def get_stats(self) -> dict:
        return {
            "total_attempts": len(self._checkpoints),
            "applied": len(self._applied),
            "rolled_back": len(self._rolled_back),
            "backup_dir": self._backup_dir,
            "recent": [
                {"id": c.id, "module": c.module_name, "verified": c.verified}
                for c in self._checkpoints[-5:]
            ],
        }


# 平台唯一实例
self_evolution = SelfEvolutionWriter()
