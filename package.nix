{ lib, stdenvNoCC, python3, makeWrapper, makeDesktopItem, copyDesktopItems
, gamescope, steam, SDL2, glib, libnotify, coreutils }:
let
  python = python3.withPackages (p: [ p.pygobject3 ]);
in
stdenvNoCC.mkDerivation {
  pname = "steam-gamescope";
  version = "1.0.2";
  src = lib.cleanSource ./.;
  nativeBuildInputs = [ makeWrapper copyDesktopItems ];
  dontBuild = true;
  doCheck = true;
  checkPhase = ''
    PYTHONDONTWRITEBYTECODE=1 ${python3}/bin/python3 -m unittest -v test_launcher
  '';
  desktopItems = [ (makeDesktopItem {
    name = "com.neg-zero.SteamGamescope";
    desktopName = "Steam (Gamescope)";
    comment = "Steam Big Picture in Gamescope on your primary display";
    exec = "steam-gamescope";
    icon = "steam";
    categories = [ "Game" ];
    startupNotify = true;
    startupWMClass = "com.neg-zero.SteamGamescope";
  }) ];
  installPhase = ''
    runHook preInstall
    install -Dm644 steam_gamescope.py "$out/libexec/steam-gamescope/steam_gamescope.py"
    makeWrapper ${python}/bin/python3 "$out/bin/steam-gamescope" \
      --add-flags "$out/libexec/steam-gamescope/steam_gamescope.py" \
      --set STEAM_GAMESCOPE_SDL_LIBRARY "${lib.getLib SDL2}/lib/libSDL2-2.0.so.0" \
      --prefix GI_TYPELIB_PATH : "${lib.getLib glib}/lib/girepository-1.0" \
      --prefix PATH : ${lib.makeBinPath [ gamescope steam libnotify coreutils ]}
    runHook postInstall
  '';
  meta = {
    description = "Steam in Gamescope using GNOME's current primary display mode";
    license = lib.licenses.mit;
    platforms = lib.platforms.linux;
    mainProgram = "steam-gamescope";
  };
}
