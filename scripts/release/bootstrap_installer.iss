; Impulse Bootstrap Installer Script
; Ships the app shell and downloads the heavy runtime/model payload during setup.

#define MyAppName "Impulse"
#define MyAppVersion "1.0.5"
#define MyAppPublisher "Impulse"
#define MyAppURL "https://github.com/Izayauh/Impulse"
#define MyAppExeName "Impulse.exe"
#define MyAppDescription "Privacy-focused, GPU-accelerated speech-to-text dictation"

[Setup]
AppId={{F7E8A9B0-1234-5678-90AB-CDEF01234567}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=Impulse-Bootstrap-Setup-{#MyAppVersion}
SetupIconFile=..\..\src\whisper_local\Impulse.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=273
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
WizardSizePercent=110
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Startup options:"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\Impulse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "_internal\models\*,_internal\cublas64_13.dll,_internal\cublasLt64_13.dll,_internal\ggml-base.dll,_internal\ggml-cpu.dll,_internal\ggml-cuda.dll,_internal\ggml.dll,_internal\whisper-cli.exe,_internal\whisper.dll"
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "..\..\USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "User Guide.txt"
Source: "..\..\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Privacy Policy.txt"
Source: "..\..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Changelog.txt"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{autoprograms}\{#MyAppName}\User Guide"; Filename: "{app}\User Guide.txt"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"

[Code]
var
  DownloadPage: TDownloadWizardPage;
  PayloadDestPaths: array of String;
  PayloadUrls: array of String;
  PayloadHashes: array of String;
  PayloadTempPaths: array of String;

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

procedure AddPayloadFile(const RelativePath, Url, Sha256: String);
var
  Index: Integer;
begin
  Index := GetArrayLength(PayloadDestPaths);
  SetArrayLength(PayloadDestPaths, Index + 1);
  SetArrayLength(PayloadUrls, Index + 1);
  SetArrayLength(PayloadHashes, Index + 1);
  SetArrayLength(PayloadTempPaths, Index + 1);

  PayloadDestPaths[Index] := RelativePath;
  PayloadUrls[Index] := Url;
  PayloadHashes[Index] := Sha256;
end;

procedure RegisterPayloadFiles;
begin
#include "bootstrap_payload.iss.inc"
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'Downloading Whisper runtime',
    'Setup is fetching the speech runtime and model files needed to finish installation.',
    nil
  );

  RegisterPayloadFiles;
end;

function InitializeSetup: Boolean;
var
  Version: TWindowsVersion;
begin
  Result := True;

  GetWindowsVersionEx(Version);

  if Version.Major < 10 then
  begin
    MsgBox('WhisperLocal requires Windows 10 or later.' + #13#10 +
           'Please upgrade your operating system.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if not IsWin64 then
  begin
    MsgBox('WhisperLocal requires 64-bit Windows.' + #13#10 +
           'This appears to be a 32-bit system.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  I: Integer;
  TempRoot: String;
  TempPath: String;
begin
  Result := '';

  if GetArrayLength(PayloadDestPaths) = 0 then
  begin
    Result := 'This bootstrap installer was built without any hosted payload configuration. Use the split GitHub release instead.';
    Exit;
  end;

  TempRoot := ExpandConstant('{tmp}\bootstrap-payload');
  ForceDirectories(TempRoot);
  DownloadPage.Clear;

  for I := 0 to GetArrayLength(PayloadDestPaths) - 1 do
  begin
    TempPath := AddBackslash(TempRoot) + PayloadDestPaths[I];
    ForceDirectories(ExtractFileDir(TempPath));
    PayloadTempPaths[I] := TempPath;
    DownloadPage.Add(PayloadUrls[I], TempPath, PayloadHashes[I]);
  end;

  try
    DownloadPage.Show;
    DownloadPage.Download;
  except
    Result := GetExceptionMessage;
  end;

  DownloadPage.Hide;
end;

procedure InstallDownloadedPayload;
var
  I: Integer;
  DestPath: String;
begin
  for I := 0 to GetArrayLength(PayloadDestPaths) - 1 do
  begin
    DestPath := ExpandConstant('{app}\' + PayloadDestPaths[I]);
    ForceDirectories(ExtractFileDir(DestPath));

    if FileExists(DestPath) then
    begin
      DeleteFile(DestPath);
    end;

    if not FileCopy(PayloadTempPaths[I], DestPath, False) then
    begin
      RaiseException('Failed to copy downloaded payload file to "' + DestPath + '".');
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    InstallDownloadedPayload;

    if not VCRedistInstalled then
    begin
      MsgBox('Note: Visual C++ Redistributable may be required.' + #13#10 + #13#10 +
             'If the application fails to start, please install the' + #13#10 +
             'Visual C++ Redistributable from Microsoft.', mbInformation, MB_OK);
    end;
  end;
end;

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

