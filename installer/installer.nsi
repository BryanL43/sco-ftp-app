; Macros
!ifndef APP_VERSION
  !error "APP_VERSION was not supplied"
!endif

!ifndef APP_NAME
  !error "APP_NAME was not supplied"
!endif

!ifndef APP_TO_PACKAGE_EXE
  !error "APP_TO_PACKAGE_EXE was not supplied"
!endif

!define DIST_DIR "..\dist"
!define UNINSTALLER_NAME "uninstall.exe"

!define MUI_ICON ".\assets\sco-logo.ico"
!define MUI_UNICON ".\assets\sco-logo.ico"

; Dependencies
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

  File "${APP_TO_PACKAGE_EXE}"

  SetOutPath "$INSTDIR\bin"
  File /r "..\bin\*"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\${UNINSTALLER_NAME}"

  ; Windows programs registry
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "AppName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "UninstallString" '"$INSTDIR\${UNINSTALLER_NAME}"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "AppVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "InstallLocation" "$INSTDIR"

  ; Shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"

  CreateShortcut \
    "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
    "$INSTDIR\${APP_NAME}.exe"

  CreateShortcut \
    "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
    "$INSTDIR\${UNINSTALLER_NAME}"

  CreateShortcut \
    "$DESKTOP\${APP_NAME}.lnk" \
    "$INSTDIR\${APP_NAME}.exe"
SectionEnd

Section "Uninstall"
  ; Remove desktop shortcut
  Delete "$DESKTOP\${APP_NAME}.lnk"

  ; Remove Start Menu shortcuts and folder
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  ; Remove application files
  RMDir /r "$INSTDIR"

  ; Remove programs entry and application registry data
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
