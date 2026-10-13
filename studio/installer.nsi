Unicode True
!include "MUI2.nsh"
Name "YCS ProcessLab Studio 0.2.0"
OutFile "release\YCS-ProcessLab-Studio-0.2.0-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\YCS ProcessLab Studio"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"
Section "YCS ProcessLab Studio" SEC01
  SetOutPath "$INSTDIR"
  File /r "dist\YCSProcessLab\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\YCS ProcessLab Studio"
  CreateShortcut "$SMPROGRAMS\YCS ProcessLab Studio\ProcessLab Studio.lnk" "$INSTDIR\YCSProcessLab.exe"
  CreateShortcut "$DESKTOP\YCS ProcessLab Studio.lnk" "$INSTDIR\YCSProcessLab.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YCSProcessLab" "DisplayName" "YCS ProcessLab Studio"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YCSProcessLab" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YCSProcessLab" "DisplayVersion" "0.2.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YCSProcessLab" "Publisher" "Yanko Creative Studio"
SectionEnd
Section "Uninstall"
  Delete "$DESKTOP\YCS ProcessLab Studio.lnk"
  RMDir /r "$SMPROGRAMS\YCS ProcessLab Studio"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\YCSProcessLab"
  RMDir /r "$INSTDIR"
  ; User projects in APPDATA intentionally survive uninstall.
SectionEnd
