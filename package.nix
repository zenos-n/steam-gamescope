{ lib, stdenvNoCC, python3, makeWrapper, makeDesktopItem, copyDesktopItems
, gamescope, steam, SDL2, glib, gtk3, wrapGAppsHook3, libnotify, coreutils
, mangohud, xvfb-run, makeFontsConf, dejavu_fonts, gobject-introspection, hicolor-icon-theme }:
let
  python = python3.withPackages (p: [ p.pygobject3 p.xlib ]);
in
stdenvNoCC.mkDerivation {
  pname = "steam-gamescope";
  version = "1.1.0";
  src = lib.cleanSource ./.;
  nativeBuildInputs = [ makeWrapper copyDesktopItems wrapGAppsHook3 gobject-introspection ];
  buildInputs = [ gtk3 hicolor-icon-theme steam ];
  dontWrapGApps = true;
  dontBuild = true;
  doCheck = true;
  nativeCheckInputs = [ xvfb-run ];
  checkPhase = ''
    test -x ${mangohud}/bin/mangoapp
    PYTHONDONTWRITEBYTECODE=1 ${python}/bin/python3 -m unittest -v test_launcher
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
    install -Dm644 loading.py "$out/libexec/steam-gamescope/loading.py"
    makeWrapper ${python}/bin/python3 "$out/libexec/steam-gamescope/session" \
      --add-flags "$out/libexec/steam-gamescope/loading.py" \
      --set STEAM_GAMESCOPE_ICON "${steam}/share/icons/hicolor/256x256/apps/steam.png" \
      --prefix XDG_DATA_DIRS : "${lib.makeSearchPath "share" [ steam hicolor-icon-theme ]}" \
      --prefix PATH : ${lib.makeBinPath [ steam ]}
    makeWrapper ${python}/bin/python3 "$out/bin/steam-gamescope" \
      --add-flags "$out/libexec/steam-gamescope/steam_gamescope.py" \
      --set STEAM_GAMESCOPE_SESSION "$out/libexec/steam-gamescope/session" \
      --set STEAM_GAMESCOPE_SDL_LIBRARY "${lib.getLib SDL2}/lib/libSDL2-2.0.so.0" \
      --prefix GI_TYPELIB_PATH : "${lib.getLib glib}/lib/girepository-1.0" \
      --prefix PATH : ${lib.makeBinPath [ gamescope steam mangohud libnotify coreutils ]}
    runHook postInstall
  '';
  postFixup = ''
    wrapGApp "$out/libexec/steam-gamescope/session"
  '';
  doInstallCheck = true;
  installCheckPhase = ''
    export PYTHONDONTWRITEBYTECODE=1
    export XDG_CACHE_HOME="$TMPDIR/cache"
    mkdir -p "$XDG_CACHE_HOME"
    makeWrapper ${python}/bin/python3 "$TMPDIR/check-loading" \
      --add-flags "$src/test_loading.py" \
      --set STEAM_GAMESCOPE_ICON "${steam}/share/icons/hicolor/256x256/apps/steam.png" \
      --prefix XDG_DATA_DIRS : "${lib.makeSearchPath "share" [ steam hicolor-icon-theme ]}" \
      "''${gappsWrapperArgs[@]}"
    STEAM_LOADING_MODULE_DIR="$out/libexec/steam-gamescope" \
      FONTCONFIG_FILE=${makeFontsConf { fontDirectories = [ dejavu_fonts ]; }} \
      xvfb-run -a -s '-screen 0 1280x720x24' "$TMPDIR/check-loading"
  '';
  meta = {
    description = "Steam in Gamescope using GNOME's current primary display mode";
    license = lib.licenses.mit;
    platforms = lib.platforms.linux;
    mainProgram = "steam-gamescope";
  };
}
