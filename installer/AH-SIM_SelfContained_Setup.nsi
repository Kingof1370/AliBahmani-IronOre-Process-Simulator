; ===========================================================================
; AH-SIM_SelfContained_Setup.nsi
; AliBahmani IronOre Process Simulator v1.0.0 - self-contained Windows setup
;
; Developer / Manufacturer : Ali Bahmani  -  Contact: 09915420558
;
; Produces ONE .exe that installs the application with its own private
; CPython 3.11 (x64) runtime and every third-party dependency (numpy, reportlab,
; ezdxf, openpyxl, Pillow, imageio + bundled ffmpeg). The target machine needs
; nothing pre-installed - not even Python.
;
; Compile (Linux / Windows / macOS):
;     makensis -DPAYLOAD=<abs payload dir> -DOUTDIR=<out dir> AH-SIM_SelfContained_Setup.nsi
; ===========================================================================

Unicode true

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!ifndef PAYLOAD
  !define PAYLOAD "payload"
!endif
!ifndef OUTDIR
  !define OUTDIR "SETUP_OUTPUT"
!endif

!define APPNAME    "AliBahmani IronOre Process Simulator"
!define SHORTNAME  "AH-SIM"
!define APPVERSION "1.0.0"
!define PUBLISHER  "Ali Bahmani"
!define PUBLISHER_FA "علی بهمنی"
!define CONTACT    "09915420558"
!define REGKEY     "Software\AliBahmani\AH-SIM"
!define OUTBASE    "AliBahmani_IronOre_Process_Simulator_Setup_v1.0.0"
!define PRODUCTDESC "Industrial Mineral Processing Simulation and Engineering Software"

Name "${APPNAME} ${APPVERSION}"
OutFile "${OUTDIR}\${OUTBASE}.exe"
InstallDir "$LOCALAPPDATA\AliBahmani\IronOreProcessSimulator"
InstallDirRegKey HKCU "${REGKEY}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64
XPStyle on
ShowInstDetails show
BrandingText "${APPNAME} v${APPVERSION}  -  ${PUBLISHER}  -  ${CONTACT}"

VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductName"      "${APPNAME}"
VIAddVersionKey /LANG=1033 "FileDescription"  "${PRODUCTDESC} (Installer)"
VIAddVersionKey /LANG=1033 "FileVersion"      "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductVersion"   "1.0.0.0"
VIAddVersionKey /LANG=1033 "CompanyName"      "${PUBLISHER}"
VIAddVersionKey /LANG=1033 "LegalCopyright"   "(c) 2026 ${PUBLISHER} - ${CONTACT}"
VIAddVersionKey /LANG=1033 "OriginalFilename" "${OUTBASE}.exe"

; --- interface strings ------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_WELCOMEPAGE_TITLE "${APPNAME} v${APPVERSION}"
!define MUI_WELCOMEPAGE_TEXT "This wizard installs ${APPNAME} v${APPVERSION} on this computer.$\r$\n$\r$\nDeveloper / Manufacturer: ${PUBLISHER} (${PUBLISHER_FA})$\r$\nContact: ${CONTACT}$\r$\n$\r$\nThe package is self-contained: it carries its own Python 3.11 (x64) runtime and all engineering libraries, so nothing has to be installed beforehand. It installs for the current user only - no administrator rights required.$\r$\n$\r$\nWhen the files are copied, setup runs a real environment self-test (it imports every library and executes one complete plant simulation) and stores the result in SELF_TEST_LOG.txt in the installation folder."
!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose the folder in which ${APPNAME} v${APPVERSION} will be installed. No administrator rights are required."
!define MUI_FINISHPAGE_TITLE "Installation of ${APPNAME} finished"
!define MUI_FINISHPAGE_TEXT "${APPNAME} v${APPVERSION} has been installed.$\r$\n$\r$\nThe environment self-test result is saved in SELF_TEST_LOG.txt in the installation folder.$\r$\n$\r$\nDeveloper / Manufacturer: ${PUBLISHER} - Contact: ${CONTACT}"
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APPNAME}"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Farsi"

; ---------------------------------------------------------------------------
; Sections
; ---------------------------------------------------------------------------

Section "Application, Python runtime and engineering libraries (required)" SEC_CORE
  SectionIn RO
  SetOutPath "$INSTDIR"

  DetailPrint "Installing application files ..."
  File /r "${PAYLOAD}\app"

  DetailPrint "Installing self-contained Python 3.11 runtime and libraries ..."
  File /r "${PAYLOAD}\runtime"
  File /r "${PAYLOAD}\bin"

  ; --- registry: identity + Add/Remove Programs entry ----------------------
  WriteRegStr HKCU "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "Version"    "${APPVERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher"  "${PUBLISHER}"
  WriteRegStr HKCU "${REGKEY}" "Contact"    "${CONTACT}"
  WriteRegStr HKCU "${REGKEY}" "Software"   "${SHORTNAME}"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "DisplayName"     "${APPNAME} v${APPVERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "DisplayVersion"  "${APPVERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "Publisher"       "${PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "DisplayIcon"     "$INSTDIR\Uninstall_AH-SIM.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "UninstallString" "$\"$INSTDIR\Uninstall_AH-SIM.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" \
      "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\Uninstall_AH-SIM.exe"

  ; --- post-install environment self-test, executed on the target machine ---
  DetailPrint "Running environment self-test (dependencies + one full simulation) ..."
  nsExec::ExecToStack '"$INSTDIR\runtime\python\python.exe" -X utf8 "$INSTDIR\bin\selfcheck.py" "$INSTDIR\app"'
  Pop $0
  Pop $1

  FileOpen $2 "$INSTDIR\SELF_TEST_LOG.txt" w
  FileWrite $2 "===============================================================$\r$\n"
  FileWrite $2 " ${APPNAME} v${APPVERSION} - environment self-test$\r$\n"
  FileWrite $2 " Developer / Manufacturer: ${PUBLISHER} - Contact: ${CONTACT}$\r$\n"
  FileWrite $2 "===============================================================$\r$\n"
  FileWrite $2 "install_dir = $INSTDIR$\r$\n"
  FileWrite $2 "exit_code   = $0   (0 = success)$\r$\n"
  FileWrite $2 "---------------------------------------------------------------$\r$\n"
  FileWrite $2 "$1$\r$\n"
  FileClose $2

  DetailPrint "self-test exit code: $0"
  ${If} $0 != "0"
    MessageBox MB_ICONEXCLAMATION|MB_OK "The environment self-test reported problems (exit code $0).$\r$\n$\r$\nThe full log was saved to:$\r$\n$INSTDIR\SELF_TEST_LOG.txt"
  ${EndIf}
SectionEnd

Section "Start Menu shortcuts" SEC_SM
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" \
      "$INSTDIR\runtime\python\pythonw.exe" \
      "$\"$INSTDIR\app\ahsim_app.py$\"" \
      "$INSTDIR\runtime\python\pythonw.exe" 0 SW_SHOWNORMAL "" "${PRODUCTDESC}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Generate Reports (Excel DXF PDF MP4).lnk" \
      "$INSTDIR\runtime\python\python.exe" \
      "$\"$INSTDIR\app\scripts\make_release.py$\"" \
      "$INSTDIR\runtime\python\python.exe" 0 SW_SHOWNORMAL "" "Regenerate all engineering outputs"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Run Test Suite.lnk" \
      "$INSTDIR\runtime\python\python.exe" \
      "-m pytest $\"$INSTDIR\app\tests$\" -v" \
      "$INSTDIR\runtime\python\python.exe" 0 SW_SHOWNORMAL "" "Run the full test suite"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Documentation.lnk" "$INSTDIR\app\docs"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall_AH-SIM.exe"
SectionEnd

Section "Desktop shortcut" SEC_DESK
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" \
      "$INSTDIR\runtime\python\pythonw.exe" \
      "$\"$INSTDIR\app\ahsim_app.py$\"" \
      "$INSTDIR\runtime\python\pythonw.exe" 0 SW_SHOWNORMAL "" "${PRODUCTDESC}"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  Delete "$INSTDIR\Uninstall_AH-SIM.exe"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\bin"
  Delete "$INSTDIR\SELF_TEST_LOG.txt"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}"
  DeleteRegKey HKCU "${REGKEY}"
SectionEnd

Function LaunchApp
  SetOutPath "$INSTDIR\app"
  Exec '"$INSTDIR\runtime\python\pythonw.exe" "$INSTDIR\app\ahsim_app.py"'
  SetOutPath "$INSTDIR"
FunctionEnd
