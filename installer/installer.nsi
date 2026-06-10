; Macros
!define APP_VERSION "1.0.0"
!define APP_NAME "ScoDexTransfer"
!define APP_TO_PACKAGE_EXE "ScoTransfer.exe"

!define DIST_DIR "..\dist"
!define UNINSTALLER_NAME "uninstall.exe"

!define MUI_ICON ".\assets\sco-logo.ico"
!define MUI_UNICON ".\assets\sco-logo.ico"

; Imports
!include "MUI2.nsh"
!include "LogicLib.nsh"

; Create dist directory if it doesn't exist
!system 'if not exist "${DIST_DIR}" mkdir "${DIST_DIR}"'

; Properties
Name "${APP_NAME}"
OutFile "${DIST_DIR}\${APP_NAME}-${APP_VERSION}-setup.exe"

; Set installer as non-administrator
RequestExecutionLevel user

; Default installation directory for first time installs
InstallDir "$LOCALAPPDATA\${APP_NAME}"

; Installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Spanish"

Function .onInit
  ; Check for an existing installation by reading the registered
  ; uninstaller command from Add/Remove Programs.
  ReadRegStr $0 HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "UninstallString"

  ; If an existing installation is found, prompt the user to remove it
  ; before continuing with the new installation.
  ${If} $0 != ""
    MessageBox MB_YESNO|MB_ICONQUESTION \
      "${APP_NAME} is already installed. Remove the existing version and continue?" \
      IDYES uninstall IDNO cancel

    uninstall:
      ExecWait '$0 /S'
      Goto done

    cancel:
      Abort

    done:
  ${EndIf}

  ; Prompt language selection
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Section
  SetOutPath "$INSTDIR"

  File "..\${APP_TO_PACKAGE_EXE}"

  SetOutPath "$INSTDIR\bin"
  File /r "..\bin\*"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\${UNINSTALLER_NAME}"

  ; Windows Add/Remove Programs registry
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "UninstallString" '"$INSTDIR\${UNINSTALLER_NAME}"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "DisplayVersion" "${APP_VERSION}"

  ; Shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_TO_PACKAGE_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\${UNINSTALLER_NAME}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_TO_PACKAGE_EXE}"
SectionEnd

Section "Uninstall"
  ; Remove desktop shortcut
  Delete "$DESKTOP\${APP_NAME}.lnk"

  ; Remove Start Menu shortcuts and folder
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  ; Remove application executable and uninstaller
  Delete "$INSTDIR\${APP_TO_PACKAGE_EXE}"
  Delete "$INSTDIR\${UNINSTALLER_NAME}"

  ; Remove application files and installation directory
  RMDir /r "$INSTDIR\bin"
  RMDir "$INSTDIR"

  ; Remove Add/Remove Programs entry and application registry data
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
