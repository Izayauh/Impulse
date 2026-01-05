; WhisperLocal Installer Script
; Built with Inno Setup (https://jrsoftware.org/isinfo.php)
; 
; This script creates a Windows installer for WhisperLocal.
; Run this with Inno Setup Compiler after building with PyInstaller.

#define MyAppName "WhisperLocal"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "WhisperLocal"
#define MyAppURL "https://github.com/Izayauh/whisper"
#define MyAppExeName "WhisperLocal.exe"
#define MyAppDescription "Privacy-focused, GPU-accelerated speech-to-text dictation"

[Setup]
; Application identity
AppId={{F7E8A9B0-1234-5678-90AB-CDEF01234567}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation settings
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes

; Output settings
OutputDir=dist
OutputBaseFilename=WhisperLocal-Setup-{#MyAppVersion}
SetupIconFile=Whisper.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression (LZMA2 for best compression ratio with large files)
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=273

; Windows version requirements
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Privileges (per-user installation supported)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Visual settings
WizardStyle=modern
WizardSizePercent=110
SetupLogging=yes

; License (create LICENSE.txt in project root)
; LicenseFile=LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Startup options:"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application and dependencies from PyInstaller build
Source: "dist\WhisperLocal\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Additional files if needed
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "User Guide.txt"
Source: "PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Privacy Policy.txt"
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Changelog.txt"

[Icons]
; Start Menu shortcuts
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{autoprograms}\{#MyAppName}\User Guide"; Filename: "{app}\User Guide.txt"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (if selected)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

; Quick Launch shortcut (if selected)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Auto-start on Windows login (if selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

; App registration for Windows Settings
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

[Run]
; Launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up user data directory on uninstall (optional - ask user?)
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Code]
// Custom Pascal Script for additional installer logic

var
  DownloadPage: TDownloadWizardPage;

// Check if Visual C++ Redistributable is installed
function VCRedistInstalled: Boolean;
var
  RegKey: String;
begin
  RegKey := 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  Result := RegKeyExists(HKEY_LOCAL_MACHINE, RegKey);
  
  if not Result then
  begin
    RegKey := 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
    Result := RegKeyExists(HKEY_LOCAL_MACHINE, RegKey);
  end;
end;

// Initialize wizard
procedure InitializeWizard;
begin
  // Create download page (for future use if needed)
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

// Check system requirements
function InitializeSetup: Boolean;
var
  Version: TWindowsVersion;
begin
  Result := True;
  
  GetWindowsVersionEx(Version);
  
  // Check Windows version (require Windows 10 or later)
  if Version.Major < 10 then
  begin
    MsgBox('WhisperLocal requires Windows 10 or later.' + #13#10 + 
           'Please upgrade your operating system.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Check for 64-bit Windows
  if not IsWin64 then
  begin
    MsgBox('WhisperLocal requires 64-bit Windows.' + #13#10 + 
           'This appears to be a 32-bit system.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
end;

// Show post-install info
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Check if VC++ Redist is missing and warn user
    if not VCRedistInstalled then
    begin
      MsgBox('Note: Visual C++ Redistributable may be required.' + #13#10 + #13#10 +
             'If the application fails to start, please install the' + #13#10 +
             'Visual C++ Redistributable from Microsoft.', mbInformation, MB_OK);
    end;
  end;
end;

// Custom uninstall - ask about user data
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    UserDataPath := ExpandConstant('{localappdata}\{#MyAppName}');
    if DirExists(UserDataPath) then
    begin
      if MsgBox('Do you want to remove your WhisperLocal settings and statistics?' + #13#10 + #13#10 +
                'Click Yes to remove all data, or No to keep your settings for future installations.',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(UserDataPath, True, True, True);
      end;
    end;
  end;
end;

