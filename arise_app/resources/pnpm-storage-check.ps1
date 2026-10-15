
$ErrorActionPreference = 'Stop';
try {
  if ($ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { throw 'policy' };
  $me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value;
  $trusted = @($me, 'S-1-5-18', 'S-1-5-32-544', 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464');
  function Test-Storage([string]$path, [bool]$allowPnpmJunction) {
  $requested = [IO.Path]::GetFullPath($path);
  $path = $requested;
  $depth = 0;
  while ($path) {
    $role = 'ancestor'; if ($depth -eq 0) { $role = 'target' } elseif ($depth -eq 1) { $role = 'parent' };
    $item = Get-Item -LiteralPath $path -Force;
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      # Accept only pnpm's known local v11 package junction, never arbitrary links.
      $base = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'pnpm'));
      $pattern = '^' + [regex]::Escape($base) + '\\global\\v11\\[^\\]+\\node_modules\\pnpm$';
      $targets = @($item.Target);
      if (-not $allowPnpmJunction -or -not $item.PSIsContainer -or
          $item.LinkType -ne 'Junction' -or $path -notmatch $pattern -or
          $targets.Count -ne 1 -or [string]::IsNullOrEmpty($targets[0])) { throw ($role + '-reparse') };
      $destination = [IO.Path]::GetFullPath($targets[0]);
      $storePattern = '^' + [regex]::Escape($base) + '\\store\\v11\\links\\@\\pnpm\\[0-9]+\.[0-9]+\.[0-9]+\\[a-f0-9]{64}\\node_modules\\pnpm$';
      if ($destination -notmatch $storePattern -or $destination -ne $targets[0]) { throw ($role + '-reparse') };
      # Validate the requested file through the destination, including every
      # destination ancestor. No further reparse point is accepted there.
      $suffix = $requested.Substring($path.Length);
      Test-Storage ($destination + $suffix) $false;
    };
    if ($item.PSIsContainer) { $acl = [IO.Directory]::GetAccessControl($path) } else { $acl = [IO.File]::GetAccessControl($path) };
    if ($trusted -notcontains $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value) { throw ($role + '-owner') };
    $allowedRights = 0x1200a9; if ($depth -ge 2) { $allowedRights = 0x1200ad };
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
      if ($rule.AccessControlType -eq 'Allow' -and -not ($rule.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -and ([long]$rule.FileSystemRights -band (-bnot [long]$allowedRights)) -and $trusted -notcontains $rule.IdentityReference.Value) { throw ($role + '-acl-mask') };
    };
    $parent = [IO.Directory]::GetParent($path);
    if ($null -eq $parent) { break }; $path = $parent.FullName; $depth++;
  };
  };
  Test-Storage $env:GENTLE_WINDOWS_CHECK $true;
  'safe'
} catch { if ($_.Exception.Message -cmatch '^(policy|(target|parent|ancestor)-(reparse|owner|acl-mask))$') { 'unsafe:' + $_.Exception.Message } else { throw } }
