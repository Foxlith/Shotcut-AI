# Compilar Shotcut AI para Windows

El código de Shotcut AI está en [github.com/Foxlith/Shotcut-AI](https://github.com/Foxlith/Shotcut-AI). Es un *fork* de Shotcut en C++ con Qt 6 y MLT 7. Hay dos formas de obtener un `shotcut.exe` que funcione.

## 1. Con GitHub Actions (recomendado)

El workflow **Build Windows (Shotcut AI)** (`.github/workflows/build-windows-shotcut-ai.yml`) compila el repositorio y genera un zip portátil.

- **Cuándo se ejecuta:** en cada *push* a `master`, `claude/**` o `fase-*` (salvo cambios solo de `.md` o `tests/`). También se lanza a mano en *Actions > Build Windows (Shotcut AI) > Run workflow*, eligiendo la rama.
- **Dónde se descarga:** en la página de la ejecución, sección *Artifacts* → `Shotcut-AI-windows-x64`. Descomprímelo en una carpeta nueva y abre `Shotcut AI.bat`.
- **Qué comprueba antes de subirlo:**
  - que todos los módulos de MLT cargan sin MSYS2;
  - que `whisper-cli.exe` arranca;
  - que Shotcut AI sigue abierto a los 60 s;
  - el servidor MCP (`tests/live_mcp_smoke.py`);
  - el servidor de análisis con un modelo de Whisper y una grabación de voz (`tests/live_analysis_smoke.py`).
- **Tiempo:** de 15 a 25 minutos.

## 2. En tu PC con MSYS2

Son los mismos pasos que el workflow.

1. Instala [MSYS2](https://www.msys2.org) y abre la terminal **MSYS2 UCRT64**.
2. Instala los paquetes (la misma lista que el workflow):

   ```bash
   pacman -Syu
   pacman -S --needed git \
     mingw-w64-ucrt-x86_64-cc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja \
     mingw-w64-ucrt-x86_64-pkgconf mingw-w64-ucrt-x86_64-qt6-base \
     mingw-w64-ucrt-x86_64-qt6-declarative mingw-w64-ucrt-x86_64-qt6-multimedia \
     mingw-w64-ucrt-x86_64-qt6-charts mingw-w64-ucrt-x86_64-qt6-websockets \
     mingw-w64-ucrt-x86_64-qt6-svg mingw-w64-ucrt-x86_64-qt6-imageformats \
     mingw-w64-ucrt-x86_64-qt6-5compat mingw-w64-ucrt-x86_64-qt6-tools \
     mingw-w64-ucrt-x86_64-qt6-translations mingw-w64-ucrt-x86_64-mlt \
     mingw-w64-ucrt-x86_64-ffmpeg mingw-w64-ucrt-x86_64-fftw \
     mingw-w64-ucrt-x86_64-frei0r-plugins mingw-w64-ucrt-x86_64-gdk-pixbuf2 \
     mingw-w64-ucrt-x86_64-libebur128 mingw-w64-ucrt-x86_64-libsamplerate \
     mingw-w64-ucrt-x86_64-libvorbis mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-rnnoise \
     mingw-w64-ucrt-x86_64-rtaudio mingw-w64-ucrt-x86_64-rubberband mingw-w64-ucrt-x86_64-sox \
     mingw-w64-ucrt-x86_64-vid.stab mingw-w64-ucrt-x86_64-whisper.cpp \
     mingw-w64-ucrt-x86_64-autotools perl-xml-parser perl-list-moreutils
   ```

   Las bibliotecas de los módulos de MLT (`libebur128`, `rubberband`, `sox`…) son dependencias *opcionales* del paquete de MLT. Sin ellas, filtros como *Size, Position & Rotate*, *Text: Simple* o *Pitch* no aparecen.
3. Descarga el código y compílalo:

   ```bash
   git clone https://github.com/Foxlith/Shotcut-AI.git
   cd Shotcut-AI
   CXXFLAGS="-DSHOTCUT_NOUPGRADE" cmake -G Ninja -S . -B build \
     -DCMAKE_BUILD_TYPE=Release -DWINDOWS_DEPLOY=OFF \
     -DCMAKE_INSTALL_PREFIX="$(cygpath -m "$PWD/dist/Shotcut-AI")"
   cmake --build build
   cmake --install build
   ```

   `-DWINDOWS_DEPLOY=OFF` hace que Shotcut y MLT busquen sus datos en `bin/..`, con la misma estructura que MSYS2.
4. Filtros de audio LADSPA (Compressor, Limiter, Reverb…; opcional). Son los plugins SWH que usa el instalador oficial:

   ```bash
   git clone --branch shotcut https://github.com/ddennedy/ladspa-swh.git deps/ladspa-swh
   (cd deps/ladspa-swh && mkdir -p m4 && ./autogen.sh --disable-nls && make -j"$(nproc)" LDFLAGS=-no-undefined)
   mkdir -p dist/Shotcut-AI/lib/ladspa && cp deps/ladspa-swh/.libs/*.dll dist/Shotcut-AI/lib/ladspa/
   ```

5. Arma la carpeta portátil, que copia melt, ffmpeg, whisper-cli, los módulos de MLT, Qt y todas las DLL:

   ```bash
   bash scripts/bundle-windows-msys2.sh dist/Shotcut-AI
   ```

6. Abre `dist/Shotcut-AI/Shotcut AI.bat`.

Después de cambiar el código, basta con repetir `cmake --build build`, `cmake --install build` y el paso 5.

## Comprobar el resultado

Con Shotcut AI abierto, en una terminal con Python 3:

```bash
python tests/live_mcp_smoke.py --read-only
python tests/live_analysis_smoke.py --server dist/Shotcut-AI/share/shotcut/mcp/shotcut_analysis.py
python tests/run_e2e_tests.py --fast
```

El primero comprueba el servidor MCP de la app y el segundo el servidor de análisis con los programas del zip. El tercero es la batería de pruebas del repositorio; no necesita la app abierta.

## En Linux

El workflow **Check Linux Build** compila con CMake, Qt 6 y MLT de Debian y ejecuta las pruebas en C++ (`ctest`). En local: `cmake -G Ninja -DSHOTCUT_BUILD_TESTS=ON -B build && cmake --build build && ctest --test-dir build`.
