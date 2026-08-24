; Impulse Installer Script
; Built with Inno Setup (https://jrsoftware.org/isinfo.php)
; 
; This script creates a Windows installer for Impulse.
; Run this with Inno Setup Compiler after building with PyInstaller.

#define MyAppName "Impulse"
#define MyAppVersion "1.0.5"
#define MyAppPublisher "Impulse"
#define MyAppURL "https://github.com/Izayauh/Impulse"
#define MyAppExeName "Impulse.exe"
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
OutputDir=..\..\dist
OutputBaseFilename=Impulse-Setup-{#MyAppVersion}
SetupIconFile=..\..\src\whisper_local\Impulse.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Enable disk spanning for large installers (>4GB)
DiskSpanning=yes

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
Source: "..\..\dist\Impulse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; WebView2 evergreen bootstrapper (the dashboard requires the WebView2
; runtime; fresh Windows 10 machines often lack it). Downloaded at build
; time by CI; skipped gracefully if absent in local builds.
Source: "..\..\runtime\prereq\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

; Additional files if needed
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "..\..\USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "User Guide.txt"
Source: "..\..\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Privacy Policy.txt"
Source: "..\..\THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Third-Party Notices.txt"
Source: "..\..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Changelog.txt"

[Icons]
; Start Menu shortcuts
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{autoprograms}\{#MyAppName}\User Guide"; Filename: "{app}\User Guide.txt"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (if selected)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

; Quick Launch shortcut (if selected)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Install the WebView2 runtime when missing - without it the dashboard
; (including license activation) cannot render. Shows the bootstrapper's
; own small UI so per-machine elevation can prompt if needed.
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/install"; StatusMsg: "Installing Microsoft WebView2 runtime (required for the dashboard)..."; Check: WebView2Missing; Flags: skipifdoesntexist

[Code]
function WebView2Missing: Boolean;
var
  Version: String;
begin
  Result := True;
  { Per-machine install }
  if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0') then
    Result := False;
  { Per-user install }
  if Result and RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0') then
    Result := False;
end;

[InstallDelete]
; Upgrading over a pre-rename WhisperLocal install: drop the old exe, shortcuts
; and autostart entry so nothing keeps launching the stale binary.
Type: files; Name: "{app}\WhisperLocal.exe"
Type: filesandordirs; Name: "{autoprograms}\WhisperLocal"
Type: files; Name: "{autodesktop}\WhisperLocal.lnk"
Type: files; Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\WhisperLocal.lnk"

[Registry]
; Auto-start on Windows login (if selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

; App registration for Windows Settings
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

; Retire the pre-rename autostart value and app key
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "WhisperLocal"; Flags: deletevalue
Root: HKCU; Subkey: "Software\WhisperLocal"; Flags: deletekey

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
    MsgBox('Impulse requires Windows 10 or later.' + #13#10 + 
           'Please upgrade your operating system.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Check for 64-bit Windows
  if not IsWin64 then
  begin
    MsgBox('Impulse requires 64-bit Windows.' + #13#10 + 
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
      if MsgBox('Do you want to remove your Impulse settings and statistics?' + #13#10 + #13#10 +
                'Click Yes to remove all data, or No to keep your settings for future installations.',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(UserDataPath, True, True, True);
      end;
    end;
  end;
end;

