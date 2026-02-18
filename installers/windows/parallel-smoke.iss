#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{D2D73B62-C0D7-4A7B-93E4-39BD7A57D889}
AppName=Parallel Smoke
AppVersion={#AppVersion}
AppPublisher=cen447
DefaultDirName={autopf}\ParallelSmoke
DefaultGroupName=Parallel Smoke
OutputDir=..\..\dist-installer
OutputBaseFilename=parallel-smoke-{#AppVersion}-windows-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "Add install folder to PATH"; GroupDescription: "Additional tasks:"; Flags: checkedonce

[Files]
Source: "..\..\dist\parallel-smoke.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\fuck.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Parallel Smoke CLI"; Filename: "{app}\parallel-smoke.exe"
Name: "{group}\Uninstall Parallel Smoke"; Filename: "{uninstallexe}"

[Code]
procedure AddPathIfMissing();
var
  PathValue: String;
  AppPath: String;
begin
  AppPath := ExpandConstant('{app}');
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', PathValue) then
    PathValue := '';

  if Pos(';' + UpperCase(AppPath) + ';', ';' + UpperCase(PathValue) + ';') = 0 then
  begin
    if (Length(PathValue) > 0) and (PathValue[Length(PathValue)] <> ';') then
      PathValue := PathValue + ';';
    PathValue := PathValue + AppPath;
    RegWriteStringValue(HKCU, 'Environment', 'Path', PathValue);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
    AddPathIfMissing();
end;

