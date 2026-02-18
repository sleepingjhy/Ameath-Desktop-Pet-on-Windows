$targets = @(
  'pet/animation.py',
  'pet/app_window.py',
  'pet/autostart.py',
  'pet/close_policy.py',
  'pet/config.py',
  'pet/idle.py',
  'pet/input.py',
  'pet/instance_manager.py',
  'pet/menu.py',
  'pet/movement.py',
  'pet/music_player.py',
  'pet/settings_store.py',
  'pet/state_machine.py',
  'pet/window.py',
  'pet/__init__.py'
)

foreach ($f in $targets) {
  $lines = Get-Content -Path $f -Encoding UTF8
  $out = New-Object System.Collections.Generic.List[string]

  for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $out.Add($line)

    $isCn = $line -match '[\u4e00-\u9fff]'
    $isComment = $line -match '^\s*#'
    $isDoc = $line -match '^\s*("""|'''''')'
    if (-not ($isCn -and ($isComment -or $isDoc))) { continue }

    $next = if ($i + 1 -lt $lines.Count) { $lines[$i + 1] } else { '' }
    $hasEn = $next -match '^\s*#\s*EN:' -or $next -match '^\s*"""\s*EN:' -or $next -match "^\s*'''\s*EN:"
    if ($hasEn) { continue }

    $indent = ''
    if ($line -match '^(\s*)') { $indent = $Matches[1] }

    if ($isComment) {
      $out.Add($indent + '# EN: Add the English translation for the Chinese comment above.')
    }
    elseif ($isDoc) {
      if ($line -match '^\s*"""') {
        $out.Add($indent + '"""EN: Add the English translation for the Chinese docstring above."""')
      }
      else {
        $out.Add($indent + "'''EN: Add the English translation for the Chinese docstring above.'''")
      }
    }
  }

  Set-Content -Path $f -Value $out -Encoding UTF8
}

Write-Output 'done'
