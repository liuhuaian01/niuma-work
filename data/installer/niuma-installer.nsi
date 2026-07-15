; ============================================================
; Super Niuma v1.0.0-alpha — NSIS Installer Script
; ============================================================

!define PRODUCT_NAME "SuperNiuma"
!define PRODUCT_VERSION "1.0.0-alpha"
!define PRODUCT_PUBLISHER "LIUHUAIAN"
!define PRODUCT_WEB_SITE "https://bbgtalk.cn"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\SuperNiuma.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

!define INSTALLER_NAME "SuperNiuma-Setup-${PRODUCT_VERSION}.exe"
!define APP_EXE "SuperNiuma.exe"

SetCompressor lzma
SetCompressorDictSize 64

; --- MUI 2.0 Modern Interface ---
!include "MUI2.nsh"

; --- MUI Settings ---
!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\niuma-icon.ico"
!define MUI_UNICON "..\assets\niuma-icon.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "欢迎安装 ${PRODUCT_NAME} v${PRODUCT_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "超级牛马工作台 — AI 驱动的本地工作台。$\r$\n$\r$\n首次启动将引导您下载推荐模型。$\r$\n建议磁盘预留 10GB 空间用于模型存储。"

; License page
!define MUI_LICENSEPAGE_CHECKBOX

; Directory page
!define MUI_DIRECTORYPAGE_TEXT_TOP "选择安装目录。$\r$\n模型文件将存储在 %APPDATA%\SuperNiuma\models\"

; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "立即启动超级牛马工作台"
!define MUI_FINISHPAGE_SHOWREADME "https://bbgtalk.cn/niuma/guide"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "查看使用指南"

; --- Pages ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; --- Installer Info ---
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
RequestExecutionLevel admin

; ============================================================
; Install Section
; ============================================================
Section "MainSection" SEC01

  SetOutPath "$INSTDIR"
  SetOverwrite on

  ; === Core executable ===
  File "..\data\dist\SuperNiuma-backend.exe"

  ; === Runtime DLLs ===
  File /r "..\data\bin\*.dll"

  ; === llama.cpp server ===
  SetOutPath "$INSTDIR\bin"
  File "..\data\bin\llama-server.exe"

  ; === Hermes Agent ===
  File "..\data\bin\hermes.exe"

  ; === Frontend static files ===
  SetOutPath "$INSTDIR\frontend"
  File /r "..\frontend-vue\dist\*"

  ; === Launcher (entry point) ===
  SetOutPath "$INSTDIR"
  ; Create launcher batch (temporary, will be replaced by proper PyInstaller launcher)
  FileOpen $0 "$INSTDIR\start-niuma.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "set NIAMA_DATA_DIR=%APPDATA%\SuperNiuma$\r$\n"
  FileWrite $0 "set NIAMA_MODELS_DIR=%APPDATA%\SuperNiuma\models$\r$\n"
  FileWrite $0 "set NIAMA_LLAMA_BIN=%INSTDIR%\bin\llama-server.exe$\r$\n"
  FileWrite $0 "start $\"$\" $\"%INSTDIR%\SuperNiuma-backend.exe$\"$\r$\n"
  FileWrite $0 "start http://127.0.0.1:18080$\r$\n"
  FileClose $0

  ; Create proper shortcut
  CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\SuperNiuma-backend.exe" "" "$INSTDIR\SuperNiuma-backend.exe" 0
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\SuperNiuma-backend.exe" "" "$INSTDIR\SuperNiuma-backend.exe" 0
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸载超级牛马.lnk" "$INSTDIR\uninst.exe" "" "$INSTDIR\uninst.exe" 0

  ; Create data directories
  CreateDirectory "$APPDATA\SuperNiuma"
  CreateDirectory "$APPDATA\SuperNiuma\models"
  CreateDirectory "$APPDATA\SuperNiuma\backend\data"
  CreateDirectory "$APPDATA\SuperNiuma\logs"
  CreateDirectory "$APPDATA\SuperNiuma\workspaces"

SectionEnd

; --- Uninstall Section ---
Section Uninstall

  ; Ask about models
  MessageBox MB_YESNO|MB_ICONQUESTION "是否同时删除已下载的模型文件？$\r$\n$\r$\n模型文件位于: $APPDATA\SuperNiuma\models" IDYES delete_models IDNO keep_models

  delete_models:
    RMDir /r "$APPDATA\SuperNiuma\models"
    RMDir /r "$APPDATA\SuperNiuma\backend"
    RMDir /r "$APPDATA\SuperNiuma\logs"
    RMDir /r "$APPDATA\SuperNiuma\workspaces"
    RMDir /r "$APPDATA\SuperNiuma\cache"
    RMDir "$APPDATA\SuperNiuma"
    Goto done_models

  keep_models:
    MessageBox MB_OK "模型文件已保留在 $APPDATA\SuperNiuma\models$\r$\n下次安装将自动恢复。"

  done_models:

  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\SuperNiuma-backend.exe"
  Delete "$INSTDIR\start-niuma.bat"
  RMDir /r "$INSTDIR\bin"
  RMDir /r "$INSTDIR\frontend"
  RMDir "$INSTDIR"

  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\*"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"

  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

  SetAutoClose true

SectionEnd

; --- Post-install ---
Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\SuperNiuma-backend.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1
SectionEnd
