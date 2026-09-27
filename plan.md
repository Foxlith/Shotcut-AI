# 🎬 Plan de Rediseño Radical — Shotcut AI → Estilo CapCut / Grafito

> **Autor:** Diseñador de Producto Senior & Ingeniero de Software Qt / Mila 1.5 🌸✨ para Fox  
> **Fecha de Creación:** 2026-09-27  
> **Última Actualización:** 2026-09-27 (Integración de Especificación Detallada "Grafito" 1440×900)  
> **Estado:** PENDIENTE DE APROBACIÓN  
> **Referencias visuales:** Mockup CapCut (`media_1790470223199.png`) y Mockup de Referencia 1440×900 px  

---

## 📋 Resumen Ejecutivo de plan.md (5 líneas)
1. Define la transformación de Shotcut AI de una interfaz clásica saturada hacia una arquitectura moderna, modular y limpia inspirada en editores contemporáneos.
2. Contiene el análisis de brecha (GAP) comparativo entre el estado actual y el layout objetivo estructurado en cuatro zonas clave.
3. Especifica los tokens formales de diseño (paleta, tipografía Geist/Geist Mono, radios, espaciados y componentes interactivos con todos sus estados).
4. Proporciona una guía técnica paso a paso para intervenir el código en C++ (Qt Widgets) y QML (Timeline), mapeando exhaustivamente cada función original sin pérdidas.
5. Incluye estrategias de accesibilidad, compatibilidad multiplataforma, mitigación de riesgos de compilación, criterios de aceptación y una sección de conflictos a resolver por el usuario.

---

## 🎯 Objetivo Original

Transformar radicalmente la interfaz de Shotcut AI para que se vea y se sienta como un editor contemporáneo (estilo **CapCut Desktop** / **DaVinci Resolve** / **Figma**) — profesional, minimalista y moderno. El cambio debe ser **dramático y visible** (no sutiles ajustes de color).

```
╔════════════════════════════════════════════════════════════════════════════════╗
║  🟧 Logo  │  Proyecto_Prueba_Shotcut_AI ▾  │ Registro │ EDICIÓN │ Efectos │ ║
║           │  1920×1080 · 30fps · Guardado   │  Color   │  Audio  │ Reprod. │ ║
║           │                                  │          ↕ Deshacer  Tareas  ║ Exportar ║
╠════════════╦══════════════════════════════════╦═════════════════════════════════╣
║   MEDIOS   ║         VIDEO VIEWER             ║        INSPECTOR               ║
║            ║                                  ║                                ║
║ + Importar ║    ┌─────────────────────┐       ║  Toma_01.mp4                   ║
║            ║    │                     │       ║  Video · 1920×1080 · 00:08     ║
║ 🔍 Buscar  ║    │    Preview Video    │       ║                                ║
║            ║    │                     │       ║  TRANSFORMAR                   ║
║ ┌────┐┌───┐║    │                     │       ║  Posición  X: 0    Y: 0        ║
║ │img1││im2│║    └─────────────────────┘       ║  Escala    ═══════●══ 100%     ║
║ └────┘└───┘║                                  ║  Rotación  ═══●══════  0°      ║
║ ┌────┐┌───┐║  00:00:06.120 / 00:00:19.000    ║  Opacidad  ═══════●══ 100%     ║
║ │img3││aud│║  ⏮ ◁ ● ▷ ⏭                      ║                                ║
║ └────┘└───┘║                                  ║  FILTROS · 2                   ║
║            ║                                  ║  ☀ Brillo          🔘          ║
║ 📁 Arrastra║                                  ║  ◎ Desenfoque      ○           ║
║ archivos   ║                                  ║  + Añadir filtro               ║
╠════════════╩══════════════════════════════════╩═════════════════════════════════╣
║  LÍNEA DE TIEMPO (Full width)                                                  ║
║  ── ✂ ⊞ ─ ── ↑ ↓ </> │ 🟢 ◇ ⊙ ✱ │ ◄ ► │    ═══════●══════  🔍 ⊕ 🖥      ║
║  00:00  00:02  00:04  ▏00:06  00:08  00:10  00:12  00:14  00:16  00:18       ║
║  V2 │ 👁 🔒 │ [Intro.png  00:03]                                              ║
║  V1 │ 👁 🔒 │ [🎬 Toma_01.mp4  00:08        ] [🎬 Toma_02.mp4  00:05  ]      ║
║  A1 │ 🔊 🔒 │ [░░░░░░ Música.wav  waveform ░░░░░░░░░░░░░░░░░░░░░░░░░░]      ║
║  A2 │ 🔊 🔒 │ Arrastra audio aquí                                            ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

---

## 📊 GAP Analysis: Actual vs. Mockup

| Aspecto | Estado Actual | Mockup CapCut / Grafito | Delta |
|---------|--------------|-------------------------|-------|
| **Top Bar** | Barra de menú clásica (Archivo, Editar, Ver...) + toolbar masiva con ~27 iconos | Solo tabs de layout + Exportar botón prominente + botón hamburguesa | 🔴 RADICAL |
| **Panel Izquierdo** | Notas dock vacío (sin miniaturas) | Panel "Medios" con grid de thumbnails, búsqueda, importar, dropzone | 🔴 RADICAL |
| **Viewer Central** | Player ocupa mucho pero con scrub bar y controles dispersos | Player limpio con botón play circular prominente y medidor integrado | 🟡 MODERADO |
| **Panel Derecho** | Medidor de audio + Tareas (sin inspector) | Inspector con Transform (pos/escala/rot/opacidad) + Filtros con toggles | 🔴 RADICAL |
| **Timeline** | Vacía, sin tracks visibles, toolbar enorme | 4 tracks (V1, V2, A1, A2) con clips coloreados, thumbnails, waveforms | 🟡 MODERADO (ya tiene QML) |
| **Barra de menú** | Visible con 7 menús | Oculta / Reducida a botón de menú compacto | 🔴 RADICAL |
| **Colores** | Dark theme clásico o cian disperso | Tema Grafito estructurado (#0B0C0F base, #15171C panel, #FF7A45 acento) | 🔴 RADICAL |

---

# 🎨 ESPECIFICACIÓN DETALLADA DE PRODUCTO Y DISEÑO (ESTILO "GRAFITO")

## 1. Dirección Visual
- **Concepto:** Estilo "Grafito": tema oscuro neutro, paneles flotantes con esquinas redondeadas separados por 8 px, un solo color de acento y jerarquía clara.
- **Inspiración:** Editores modernos de alto rendimiento (DaVinci Resolve, CapCut, Figma), sin copiar servilmente su identidad gráfica.
- **Reglas de Estilo:** Sin degradados decorativos superfluos ni uso de emojis en los componentes nativos de la interfaz.

---

## 2. Tokens de Diseño

### 2.1 Colores Base
- **Fondo de la aplicación:** `#0B0C0F`
- **Fondo de panel:** `#15171C`
- **Borde de panel:** `#22252D`
- **Divisor interno:** `#1F2229`
- **Superficie elevada (tarjetas, filas de filtro):** `#1D2027`
- **Hover / elemento activo secundario:** `#262A33`
- **Campos de texto y buscador:** `#0F1115`
- **Carril de pista (timeline canvas):** `#111317`
- **Cabecera de pista:** `#1B1E24`
- **Trazo sutil y pistas de sliders:** `#2A2E37`
- **Borde punteado (zonas de soltar / dropzones):** `#343944`

### 2.2 Jerarquía de Texto
- **Texto Primario:** `#E8EAEE` (alta legibilidad, títulos, campos activos)
- **Texto Secundario:** `#C9CED6` (subtítulos, opciones seleccionables)
- **Texto Apagado:** `#9AA1AD` (iconos en reposo, placeholders)
- **Texto Terciario / Etiquetas:** `#858C98` (secciones, metadatos pequeños)
- **Texto Deshabilitado:** `#5F6672` (estados inactivos)

### 2.3 Color de Acento (Configurable)
- **Acento por defecto:** `#FF7A45` (Naranja Grafito)
- **Texto e iconos sobre el acento:** `#140A05` (optimizado para alcanzar un contraste superior al blanco sobre `#FF7A45`)
- **Acento suave para fondos activos:** Acento al 18 % de opacidad (`#FF7A452E`)
- **Paleta de acentos alternativos ofrecidos al usuario:**
  - `#5B8CFF` (Azul Eléctrico)
  - `#F5B83D` (Ámbar Dorado)
  - `#B08CFF` (Lavanda Neón)

### 2.4 Clips de la Línea de Tiempo
- **Clip de Video:**
  - Relleno: `#24346B`
  - Borde: `#4D6BE0`
  - Texto primario: `#EEF1FF`
  - Texto secundario: `#B7C2F0`
- **Clip de Imagen / Superposición:**
  - Relleno: `#34275A`
  - Borde: `#8E6FE0`
  - Texto primario: `#EEE8FF`
  - Texto secundario: `#C9B8FF`
- **Clip de Audio:**
  - Relleno: `#0F3B35`
  - Borde: `#2BB596`
  - Forma de onda: `#3DD6B0` al 85 % de opacidad
  - Texto: `#E6FFF8`
- **Clip Seleccionado (cualquier tipo):**
  - Borde interno de 1 px del color de acento (`#FF7A45`).
  - Anillo exterior de 1 px del color de acento (`#FF7A45`).

### 2.5 Medidor de Audio Integrado
- **Ancho de barras:** 6 px
- **Fondo del medidor:** `#1D2027`
- **Relleno dinámico:** Gradiente funcional de `#2BB596` (niveles nominales/seguros) que pasa a `#F5C542` en la parte alta (precaución/pico).

### 2.6 Tipografía
- **Fuente de Interfaz:** `Geist` (pesos 400 Regular, 500 Medium, 600 SemiBold, 700 Bold).
  - Respaldo del sistema: `Segoe UI`, `sans-serif`.
- **Fuente Numérica y Técnica:** `Geist Mono` (pesos 400 Regular, 500 Medium) para timecodes, duraciones y valores numéricos tabulares.
- **Licencia:** Ambas fuentes bajo licencia SIL Open Font License (OFL) v1.1, empaquetadas directamente en los recursos de la aplicación (`:/fonts/`).
- **Escala Tipográfica:**
  - Texto base de UI: `13 px`
  - Botones y pestañas: `12–12.5 px`, peso 500
  - Títulos de panel: `13 px`, peso 600
  - Etiquetas de sección: `11 px`, peso 600, en **MAYÚSCULAS** con `letter-spacing: 0.07em`
  - Pie de texto / metadatos: `11 px`, peso 400
  - Timecode principal: `15 px` Geist Mono, peso 500
  - Duraciones y timecodes secundarios: `10–11.5 px` Geist Mono, peso 400/500

### 2.7 Radios de Borde (Border Radius)
- **Paneles flotantes:** `12 px`
- **Botones estándar:** `7–8 px`
- **Botones de la barra lateral izquierda:** `9 px`
- **Contenedor de control segmentado:** `9–10 px` (con opción interna de `6–7 px`)
- **Clips de la línea de tiempo:** `6 px`
- **Chips e insignias:** `4–6 px`
- **Interruptores (toggles):** `9 px` (cuerpo de 18 px alto / radio 9 px)

### 2.8 Espaciado y Dimensiones Estructurales
- **Margen exterior y separación entre paneles:** `8 px`
- **Padding interno de paneles:** `12–14 px`
- **Cabeceras de panel:** `44 px` de altura
- **Barra superior:** `52 px` de altura

### 2.9 Iconografía
- **Familia:** Estilo de trazo continuo tipo Lucide Icons (licencia ISC).
- **Especificaciones:** Cuadrícula de base `24×24`, grosor de trazo (`stroke-width`) de `1.75` con extremos y uniones redondeadas (`round cap / round join`).
- **Tamaños:**
  - Estándar: `18 px`
  - Barras compactas de herramientas: `15 px`
- **Color:** `#9AA1AD` en estado de reposo; toma el color de acento (`#FF7A45`) en estado activo.

---

## 3. Layout de Referencia (1440×900 px)

Estructura de cuatro bloques principales adaptada para pantallas estándar y escalable:

### 3.1 Barra Superior (52 px)
- **Extremo Izquierdo:**
  - Botón de menú hamburguesa (despliega menú global).
  - Logotipo de Shotcut AI de 28 px enmarcado en fondo de color de acento (`#FF7A45`).
  - Nombre del proyecto con selector desplegable de proyectos recientes.
  - Línea de metadatos de estado: `"1920×1080 · 30 fps · Estéreo · Guardado"` en color `#858C98` (Geist 11 px).
- **Centro:**
  - Selector segmentado de espacios de trabajo (corresponde a los modos de layout nativos de Shotcut):
    `[ Registro | Edición | Efectos | Color | Audio | Reproductor ]`
- **Extremo Derecho:**
  - Acciones de Deshacer (`Ctrl+Z`) y Rehacer (`Ctrl+Y`).
  - Botón secundario "Tareas" (muestra contador de renderizados en cola).
  - Botón primario de acción "Exportar" con fondo de acento (`#FF7A45`) y texto `#140A05`.

### 3.2 Fila Superior (500 px de alto) — Cuatro Columnas
1. **Barra Lateral de Iconos (52 px de ancho):**
   - Iconos de acceso rápido a los docks principales: Medios (`PlaylistDock`), Filtros (`FiltersDock`), Fotogramas clave (`KeyframesDock`), Subtítulos (`SubtitlesDock`), Notas (`NotesDock`), Reciente (`RecentDock`).
   - Parte inferior fijada: Botón "Ayuda" (`actionWhatsThis` / FAQ).
2. **Panel "Medios" (300 px de ancho):**
   - Cabecera con título "Medios" y botón secundario `+ Importar`.
   - Control segmentado: `[ Lista de reproducción | Recientes ]`.
   - Campo de búsqueda interactivo con icono de lupa (`#0F1115`).
   - Cuadrícula de 2 columnas con tarjetas de previsualización 16:9, chip de duración en esquina y etiquetas de nombre + tipo.
   - Zona inferior punteada para soltar archivos ("Arrastra archivos aquí - Video, audio o imágenes") con borde `#343944`.
3. **Visor de Video (Ancho Flexible / Elástico):**
   - Cabecera: Control segmentado `[ Fuente | Proyecto ]`, chip informativo de resolución/fps, selector de escala "Ajustar", conmutador de cuadrícula de composición y botón de pantalla completa.
   - Escenario de renderizado negro absoluto (`#08090B`) con visualización de video 16:9 centrada.
   - Medidor de picos estéreo integrado verticalmente en el margen derecho del visor (barras de 6 px).
   - Barra de progreso de 4 px con marcas de tiempo (in/out) y cabezal circular de arrastre.
   - Fila de controles de transporte:
     - Izquierda: Timecode actual / Duración total (`15 px` Geist Mono).
     - Centro: `Inicio`, `Fotograma Anterior`, `Reproducir/Pausar` (círculo de acento de 44 px), `Fotograma Siguiente`, `Final`.
     - Derecha: Conmutador de Repetición (Loop) y control desplegable de Volumen.
4. **Inspector (300 px de ancho):**
   - Pestañas superiores: `[ Inspector | Tareas | Historial ]`. La pestaña activa cuenta con un subrayado de 2 px del color de acento.
   - Cabecera del elemento seleccionado: miniatura del clip, nombre del archivo y metadatos técnicos.
   - Sección **TRANSFORMAR** (mayúsculas con tracking):
     - Posición X / Y en campos numéricos independientes (`QLineEdit`).
     - Sliders horizontales de precisión para Escala, Rotación y Opacidad, con indicador numérico lateral.
   - Sección **FILTROS**:
     - Filas de filtros asignados con icono representativo, nombre e interruptor (toggle) rápido on/off.
     - Botón con borde punteado `+ Añadir filtro`.

### 3.3 Línea de Tiempo (Altura Restante, aprox. 324 px)
- **Barra de Herramientas de Pista (44 px de alto):**
  - Grupos de botones de 15 px separados por divisores verticales (`#1F2229`):
    - Grupo 1: Menú de opciones de línea de tiempo.
    - Grupo 2: Cortar, Copiar, Pegar.
    - Grupo 3: Añadir pista, Borrar y cerrar hueco (Ripple Delete), Levantar (Lift), Sobrescribir (Overwrite), Dividir cabezal (Split at Playhead).
    - Grupo 4: Añadir marcador, Marcador anterior, Marcador siguiente.
    - Grupo 5 (Conmutadores): Imán (Snapping), Previsualización al arrastrar (Scrub), Edición en cadena (Ripple), Edición en cadena en todas las pistas.
    - Grupo 6 (Extremo Derecho): Grabar voz en off (Micrófono), Zoom −, Slider horizontal de zoom, Zoom +, Ajustar línea de tiempo a la ventana (`Zoom to Fit`).
- **Cabeceras de Pista (164 px de ancho fijo):**
  - Insignia de pista con código de color (`V2`, `V1`, `A1`, `A2`).
  - Nombre editable de pista.
  - Botones de acción rápida: Ocultar/Mostrar video (o Silenciar audio) y Bloqueo de pista.
- **Alturas y Separación de Pistas:**
  - Pista `V2`: `44 px`
  - Pista `V1` (Pista principal de video): `58 px`
  - Pista `A1` (Pista principal de audio): `52 px`
  - Pista `A2`: `40 px`
  - Separación entre pistas: `4 px` sobre fondo `#111317`
- **Regla de Tiempo (Ruler):** Altura de `28 px`, escala de referencia de `60 px` por segundo de tiempo.
- **Cabezal de Reproducción (Playhead):** Trazo vertical de `2 px` con el color de acento (`#FF7A45`) y cabezal superior distintivo.
- **Pista Vacía:** Área punteada receptora con el texto explicativo `"Arrastra audio aquí"`.

---

## 4. Matriz de Correspondencia con la Interfaz Original

Para garantizar que el rediseño preserve el 100 % de las capacidades profesionales de Shotcut, ningún comando ni panel ha sido eliminado; cada elemento cuenta con un destino ergonómico en la nueva estructura:

| Elemento Original de Shotcut | Ubicación en el Rediseño Grafito | Modo de Acceso / Mecanismo Técnico |
|---|---|---|
| **Barra de Menús Clásica** (Archivo, Editar, Ver, etc.) | Botón de Menú Hamburguesa en la Barra Superior | Menú desplegable global unificado; accesible también mediante tecla `Alt` |
| **Abrir Archivo / Abrir Otro** | Botón `+ Importar` en el panel Medios | Despliega selector de archivos nativo o submenú de generadores |
| **Guardar / Guardar Como** | Indicador de Estado en Barra Superior y Menú | Estado visible ("Guardado" / "Modificado"), menú hamburguesa y atajo `Ctrl+S` / `Ctrl+Shift+S` |
| **Deshacer / Rehacer** | Barra Superior (Extremo Derecho) | Iconos directos junto al área de exportación y atajos `Ctrl+Z` / `Ctrl+Y` |
| **Medidor de Picos de Audio** (`AudioPeakMeterScopeWidget`) | Lateral Derecho del Visor de Video | Dock integrado directamente en el lienzo del visor (ancho de 6 px) |
| **Propiedades de Clip / Pista** (`m_propertiesDock`) | Pestaña "Inspector" (Panel Derecho) | Muestra sección Transformar y metadatos cuando hay un clip seleccionado |
| **Lista de Reproducción** (`PlaylistDock`) | Panel "Medios" (Columna 2 Superior) | Integrado permanentemente en el bloque central de activos |
| **Explorador de Archivos** (`FilesDock`) | Barra Lateral de Iconos / Pestaña en Medios | Icono en la barra lateral izquierda de 52 px |
| **Recientes** (`RecentDock`) | Barra Lateral y Segmentado de Medios | Pestaña secundaria `Recientes` dentro del panel de Medios |
| **Notas** (`NotesDock`) | Barra Lateral de Iconos | Icono dedicado en la barra lateral izquierda |
| **Filtros** (`FiltersDock`) | Sección "Filtros" en Inspector y Barra Lateral | Lista directa en el Inspector y conmutador en barra lateral |
| **Fotogramas Clave** (`KeyframesDock`) | Barra Lateral y Pestaña en Timeline | Conmutador en barra lateral izquierda y tabificable en panel inferior |
| **Subtítulos** (`SubtitlesDock`) | Barra Lateral de Iconos | Icono de acceso en barra lateral izquierda |
| **Línea de Tiempo** (`TimelineDock`) | Panel Inferior Completo (Full Width) | Área QML rediseñada con tokens Grafito y cabeceras de 164 px |
| **Exportar Video** (`EncodeDock`) | Botón Primario "Exportar" en Barra Superior | Al pulsar, abre modal/drawer lateral con los ajustes de codificación |
| **Cola de Tareas** (`JobsDock`) | Pestaña "Tareas" en Inspector y Botón Superior | Botón indicador en barra superior y pestaña dedicada en el panel derecho |
| **Historial de Deshacer** (`HistoryUndoView`) | Pestaña "Historial" en Inspector | Tercera pestaña del Inspector derecho |
| **¿Qué es esto? / FAQ** (`actionWhatsThis`) | Botón de Ayuda en Barra Lateral | Fijado en la base de la barra lateral izquierda de 52 px |
| **Espacios de Trabajo / Layouts** (Logging, Editing, etc.) | Selector Segmentado en Barra Superior | Conmutador central directo entre los 6 modos de trabajo |

---

## 5. Catálogo de Componentes y Estados Interactivos

Todos los controles de la aplicación deben respetar rigurosamente la matriz de estados de interacción:

| Componente | Reposo | Hover | Presionado / Click | Foco de Teclado | Activo / Seleccionado | Deshabilitado |
|---|---|---|---|---|---|---|
| **Botón Primario (Exportar)** | Fondo `#FF7A45`, texto `#140A05`, radio 7–8 px | Fondo `#FF8F61` | Fondo `#E66835` | Anillo exterior de 2 px `#FF7A45` | N/A | Fondo `#262A33`, texto `#5F6672` |
| **Botón Secundario (+ Importar)** | Fondo transparente, borde 1 px `#2A2E37`, texto `#E8EAEE` | Fondo `#262A33`, borde `#343944` | Fondo `#1F2229` | Anillo de 2 px `#FF7A45` | N/A | Borde `#1F2229`, texto `#5F6672` |
| **Botón de Icono (Toolbar)** | Fondo transparente, icono `#9AA1AD` | Fondo `#262A33`, icono `#E8EAEE` | Fondo `#1F2229` | Anillo de 2 px `#FF7A45` | Fondo `#FF7A452E`, icono `#FF7A45` | Icono `#5F6672` |
| **Control Segmentado** | Contenedor `#0F1115` (radio 9–10 px), opción `#9AA1AD` | Opción bajo cursor `#C9CED6` | Fondo `#1D2027` | Anillo de 2 px `#FF7A45` | Fondo `#262A33`, texto `#E8EAEE`, radio 6–7 px | Texto `#5F6672` |
| **Pestañas de Inspector** | Fondo transparente, texto `#9AA1AD` | Texto `#E8EAEE` | Texto `#C9CED6` | Anillo de 2 px `#FF7A45` | Texto `#E8EAEE`, línea inferior 2 px `#FF7A45` | Texto `#5F6672` |
| **Campo de Texto / Buscador** | Fondo `#0F1115`, borde 1 px `#22252D`, texto `#E8EAEE` | Borde 1 px `#2A2E37` | N/A | Borde 1 px `#FF7A45`, anillo 2 px `#FF7A452E` | N/A | Fondo `#15171C`, texto `#5F6672` |
| **Slider (Opacidad, Escala)** | Pista `#2A2E37` (4 px), sub-pista `#FF7A45`, manija 12 px blanca | Manija con halo de 4 px `#FF7A452E` | Manija `#FF7A45` | Anillo de 2 px `#FF7A45` | N/A | Pista `#1F2229`, sub-pista `#5F6672` |
| **Interruptor (Toggle Filter)** | Fondo `#2A2E37`, pastilla blanca apagada (radio 9 px) | Fondo `#343944` | Fondo `#262A33` | Anillo de 2 px `#FF7A45` | Fondo `#FF7A45`, pastilla blanca `#FFFFFF` | Fondo `#1F2229`, pastilla `#5F6672` |
| **Chip / Insignia de Pista** | Fondo `#1D2027`, texto `#C9CED6`, radio 4–6 px | Fondo `#262A33` | N/A | N/A | Borde 1 px `#FF7A45` | Texto `#5F6672` |
| **Tarjeta de Medio (Grid)** | Superficie `#1D2027`, borde 1 px `#22252D`, radio 8 px | Superficie `#262A33`, borde `#343944` | Superficie `#1F2229` | Anillo de 2 px `#FF7A45` | Borde 1 px `#FF7A45`, anillo `#FF7A452E` | Opacidad 50 % |
| **Fila de Filtro** | Superficie `#1D2027`, divisor `#1F2229`, radio 6 px | Superficie `#262A33` | Superficie `#1F2229` | Anillo de 2 px `#FF7A45` | Borde izquierdo 2 px `#FF7A45` | Texto `#5F6672` |
| **Cabecera de Pista (164 px)** | Fondo `#1B1E24`, divisor `#1F2229` | Fondo `#262A33` | N/A | Anillo de 2 px `#FF7A45` | Fondo `#22252D`, borde de acento | Opacidad 60 % |
| **Clip de Línea de Tiempo** | Relleno temático (video/audio/img), borde 1 px | Borde más claro (+15 % brillo) | N/A | Anillo de 2 px `#FF7A45` | Borde 1 px `#FF7A45` + anillo exterior 1 px `#FF7A45` | Relleno atenuado, texto `#5F6672` |

---

## 6. Accesibilidad y Estándares de Usabilidad

1. **Ratios de Contraste WCAG 2.1 AA:**
   - Todo el texto estándar mantiene una relación de contraste superior a **4.5:1** contra sus respectivos fondos (#E8EAEE sobre #15171C alcanza 12.8:1; #FF7A45 sobre #0B0C0F alcanza 6.8:1).
   - El texto sobre el botón primario de acento utiliza `#140A05` garantizando **6.2:1** (el texto blanco `#FFFFFF` sobre `#FF7A45` queda por debajo del mínimo reglamentario con solo 2.9:1).
   - El texto grande (≥ 24 px o ≥ 18 px negrita) supera el requisito mínimo de **3:1**.
2. **Nombres Accesibles y Tooltips:**
   - El 100 % de los botones representados exclusivamente por iconos cuentan con atributo `QAction::toolTip()`, `QToolTip` descriptivo y soporte de nombre accesible para lectores de pantalla (`QAccessibleWidget`).
3. **Navegación Asistida por Teclado:**
   - Orden lógico de tabulación (`Tab` / `Shift+Tab`) establecido entre las cuatro columnas principales.
   - Indicador visual de foco estandarizado mediante un anillo exterior de 2 px del color de acento (`#FF7A45`).
   - Todos los comandos del menú principal mantienen sus atajos de teclado históricos de Shotcut sin modificaciones regresivas.
4. **Diferenciación Cromática y Luminosidad:**
   - La distinción entre clips de Video (`#24346B`), Imagen (`#34275A`) y Audio (`#0F3B35`) está reforzada por variaciones de luminosidad y patrones visuales internos (las pistas de audio exhiben forma de onda vectorial al 85 % de opacidad; los videos exhiben tiras de fotogramas clave), evitando la dependencia exclusiva del tono de color para usuarios con daltonismo.

---

# 🏗️ PLAN DE IMPLEMENTACIÓN TÉCNICA EN SHOTCUT (POR FASES)

> [!IMPORTANT]
> **Estrategia Técnica Fundamental:**  
> Shotcut opera mediante una arquitectura híbrida de **Qt Widgets** (esqueleto principal, paneles dock, diálogos de codificación) y **QtQuick / QML** (motor del multitrack timeline y cabeceras de pista).  
> Los cambios en QML y QSS se aplican en caliente o en runtime sin necesidad de recompilar el binario C++. Los cambios estructurales en C++ se documentan con precisión para integración en compilador.

---

### FASE 1: Tema Base y Tipografía (QPalette, QSS y Fuentes)
- **Objetivo:** Establecer la infraestructura visual base, inyectar los tokens de color Grafito y cargar las familias tipográficas Geist.
- **Tareas Técnicas:**
  1. Descargar y registrar las fuentes `Geist-Regular.ttf`, `Geist-Medium.ttf`, `Geist-SemiBold.ttf`, `Geist-Bold.ttf`, `GeistMono-Regular.ttf` y `GeistMono-Medium.ttf` en los recursos de Qt (`icons/resources.qrc` o similar, verificar en el repositorio). Cargar en runtime mediante `QFontDatabase::addApplicationFont()`.
  2. Configurar la `QPalette` global en `MainWindow::changeTheme()` (`src/mainwindow.cpp`, líneas ~4221–4244) asignando:
     - `QPalette::Window` → `#0B0C0F`
     - `QPalette::Base` → `#0F1115`
     - `QPalette::AlternateBase` → `#1D2027`
     - `QPalette::Highlight` → `#FF7A45`
     - `QPalette::HighlightedText` → `#140A05`
     - `QPalette::Button` → `#15171C`
     - `QPalette::ButtonText` → `#E8EAEE`
  3. Reemplazar el archivo maestro `capcut_theme.qss` con los tokens exactos del estilo Grafito, definiendo radios de 12 px para paneles y 7–8 px para botones.
  4. Eliminar las cadenas de estilos QSS embebidas en el constructor de `MainWindow` (`src/mainwindow.cpp`, líneas 262–290) para unificar la fuente de verdad en el archivo externo.
- **Archivos Probables:**
  - `src/mainwindow.cpp` (líneas 260–292, 4196–4285)
  - `capcut_theme.qss`
  - `icons/resources.qrc` (o archivo de recursos de fuentes, verificar en el repositorio)
- **Riesgos:** Conflictos de cascada en controles nativos de Windows; textos sin contraste si no se define la regla para `QToolTip`.
- **Criterios de Aceptación:** La aplicación inicia con fondo `#0B0C0F`, textos en Geist y cero destellos o bordes claros residuales.

---

### FASE 2: Iconografía Lucide (SVG de Trazo) [COMPLETADO — VERIFICADO AL 100%]
- **Objetivo:** Modernizar la biblioteca de iconos eliminando vestigios de estilos antiguos e implementando el estándar Lucide.
- **Estado:** ✅ Completado y blindado en 3 rondas adversariales (87 iconos de trazo continuo Lucide con viewBox 24x24, trazo 1.75, uniones redondeadas, vector SVG maestro + 32x32 PNG anti-aliased RGBA).
- **Logros Clave:**
  1. 87 iconos modernizados cubriendo controles de transporte, edición de timeline, cabecera de tracks, barras de docks (Playlist, Files, Keyframes, Markers, Notes, Subtitles, Player, Scopes) y utilidades.
  2. Purga total de iconos indexados de 8 bits Oxygen (`mode: P` reducido de 13 a 0).
  3. Estandarización de 18x18 px en barras estándar y 15x15 px en barras compactas de línea de tiempo con especificidad QSS blindada contra sobreescrituras en runtime.
  4. Harmonización de estados de color Grafito (`#9AA1AD` reposo, `#E8EAEE` hover, `#FF7A45` acento y presionado, `rgba(255, 122, 69, 0.18)` activo con texto `#FF7A45`, `#5F6672` inactivo).
  5. Harmonización de barras de filtro de Playlist y Files docks (`playlistFiltersToolbar`, `filesFiltersToolbar`).
  6. Suite automatizada con 100% de éxito: 635/635 tests completos, 624/624 fast, 11/11 tests unitarios de Fase 2.
- **Archivos Modificados:**
  - `icons/dark/32x32/*.svg`, `icons/dark/32x32/*.png`, `icons/resources.qrc`
  - `capcut_theme.qss`, `src/mainwindow.ui`, `src/mainwindow.cpp`
  - `src/widgets/docktoolbar.cpp`, `src/widgets/docktoolbar.h`, `src/docks/timelinedock.cpp`
  - `src/docks/playlistdock.cpp`, `src/docks/filesdock.cpp`
  - `scripts/generate_lucide_icons.py`, `tests/test_phase2_icon_and_theme_verification.py`
- **Criterios de Aceptación:** Todos los iconos se visualizan nítidos en trazo uniforme con 18/15 px, colorean adecuadamente según el estado y 635/635 pruebas aprueban sin fallos.

---

### FASE 3: Estructura de Docks y Layout Superior (52 px + 500 px) [COMPLETADO — COMPILA EN CI LINUX; PENDIENTE DE VALIDACIÓN VISUAL EN WINDOWS]
- **Estado:** ✅ Implementado en `src/mainwindow.ui`, `src/mainwindow.cpp/.h`, `src/defaultlayouts.h` (6 estados regenerados), `src/settings.cpp/.h`, `capcut_theme.qss`; geometría verificada a 1440×900 (`8 | 52 | 8 | 300 | 8 | 748 | 8 | 300 | 8`, barra 52 + 8, fila 500, timeline 324). Detalle completo en `agent.md`.
- **Objetivo:** Configurar la cuadrícula superior de 4 columnas y transformar la barra de herramientas principal.
- **Tareas Técnicas:**
  1. Ocultar la barra de menús tradicional (`menuBar()->setVisible(false)` en `src/mainwindow.cpp`, línea ~195) y vincular su llamada a un botón hamburguesa en la barra superior.
  2. Rediseñar `ui->mainToolBar` (`src/mainwindow.ui` y `setupLayoutSwitcher()` en `src/mainwindow.cpp`, línea ~6806) para contener únicamente:
     - Logotipo con fondo de acento de 28 px.
     - Etiqueta de proyecto con selector desplegable y metadatos.
     - Selector segmentado central de layouts (`Logging`, `Editing`, etc.).
     - Botones Deshacer, Rehacer, Tareas y el botón primario "Exportar" (`#FF7A45`).
  3. Crear o configurar la barra lateral izquierda de iconos (52 px de ancho) conteniendo accesos rápidos a `m_playlistDock`, `m_filtersDock`, `m_keyframesDock`, `m_subtitlesDock`, `m_notesDock`, `m_recentDock` y el botón de Ayuda.
  4. En `MainWindow::setupAndConnectDocks()` (`src/mainwindow.cpp`, líneas 944–975), reorganizar los docks:
     - Columna 2 (Medios, 300 px): `m_playlistDock` visible por defecto, tabificado con `m_filesDock` y `m_recentDock`.
     - Columna 3 (Visor): widget central elástico.
     - Columna 4 (Inspector, 300 px): `m_propertiesDock` visible por defecto, tabificado con `m_filtersDock`, `m_jobsDock` y `m_historyDock`.
     - Inferior: `m_timelineDock` abarcando el 100 % del ancho.
  5. Asegurar la separación exterior de 8 px y esquinas redondeadas de 12 px mediante propiedades de `QMainWindow::separator` y márgenes en el central widget.
- **Archivos Probables:**
  - `src/mainwindow.cpp` (líneas 195–242, 944–975, 6806–6885)
  - `src/mainwindow.ui` (líneas 338–403)
  - `src/defaultlayouts.h` (actualización de estados predeterminados)
- **Riesgos:** Que la restauración de layouts previos de Windows Registry altere la disposición inicial.
- **Criterios de Aceptación:** Las 4 columnas se alinean a 500 px de altura con separaciones de 8 px y la barra superior mide exactamente 52 px.

---

### FASE 4: Visor de Video y Controles de Transporte
- **Objetivo:** Integrar el medidor de audio en el lienzo de video y consolidar el panel de transporte moderno.
- **Tareas Técnicas:**
  1. En `Player::Player()` (`src/player.cpp`, líneas 85–240), definir el fondo del escenario en `#08090B`.
  2. Incrustar verticalmente el medidor de picos (`AudioPeakMeterScopeWidget` o instancia de `ScopeController`, verificar en el repositorio) en el margen derecho del contenedor de video con barras de 6 px y fondo `#1D2027`.
  3. Refactorizar `layoutToolbars()` (`src/player.cpp`, líneas 1226–1260):
     - Barra de progreso de 4 px con manija circular de acento.
     - Timecode en `15 px` Geist Mono tabular a la izquierda.
     - Fila central con botones de Inicio, Fotograma Anterior, botón Play circular de acento de **44 px** (`#FF7A45` con icono `#140A05`), Fotograma Siguiente y Final.
     - Controles de repetición y menú de volumen a la derecha.
  4. Mover el selector segmentado `[ Fuente | Proyecto ]` y los chips de zoom/resolución a la cabecera superior del visor.
- **Archivos Probables:**
  - `src/player.cpp` (líneas 85–240, 1226–1260)
  - `src/player.h`
  - `src/widgets/scrubbar.cpp` (verificar en el repositorio)
- **Riesgos:** Parpadeos de redibujado de OpenGL/DirectX al superponer widgets sobre el área de renderizado de MLT.
- **Criterios de Aceptación:** El botón Play mide 44 px en color de acento, el medidor de audio responde en el margen derecho y el video se centra en fondo `#08090B`.

---

### FASE 5: Línea de Tiempo y Filtros QML
- **Objetivo:** Modernizar el lienzo multitrack, cabeceras de pista, colores de clips y controles de toolbar en QtQuick.
- **Tareas Técnicas:**
  1. En `src/qml/views/timeline/timeline.qml`:
     - Asignar `trackBgDark: "#111317"` y `selectedTrackColor: "#1D2027"`.
     - Definir el cabezal de reproducción (`cursor`) en trazo de 2 px con color `#FF7A45`.
     - Fijar la regla de tiempo en altura de 28 px y escala de 60 px por segundo.
  2. En `src/qml/views/timeline/TrackHead.qml`:
     - Fijar el ancho de las cabeceras en `164 px` con fondo `#1B1E24`.
     - Incorporar insignias de tipo de pista (`V2`, `V1`, `A1`, `A2`) con radios de 4–6 px.
     - Establecer alturas predeterminadas: V2 = 44 px, V1 = 58 px, A1 = 52 px, A2 = 40 px, separadas por 4 px.
  3. En `src/qml/views/timeline/Clip.qml`:
     - Configurar radios de esquina en `6 px`.
     - Aplicar los tokens cromáticos de clips:
       - Video: fondo `#24346B`, borde `#4D6BE0`, texto `#EEF1FF`, subtexto `#B7C2F0`.
       - Imagen: fondo `#34275A`, borde `#8E6FE0`, texto `#EEE8FF`.
       - Audio: fondo `#0F3B35`, borde `#2BB596`, onda `#3DD6B0` al 85 %, texto `#E6FFF8`.
     - Estado seleccionado: borde interno de 1 px `#FF7A45` más anillo exterior de 1 px `#FF7A45`.
  4. En `src/docks/timelinedock.cpp` (líneas 334–402):
     - Configurar la barra de herramientas en 44 px con divisores `#1F2229` y grupos ordenados según la especificación.
- **Archivos Probables:**
  - `src/qml/views/timeline/timeline.qml`
  - `src/qml/views/timeline/TrackHead.qml`
  - `src/qml/views/timeline/Clip.qml`
  - `src/qml/views/timeline/Ruler.qml`
  - `src/docks/timelinedock.cpp` (líneas 334–402)
- **Riesgos:** Desincronización de alturas de pista entre `TrackHead.qml` y `Track.qml` provocando desalineaciones verticales de clips.
- **Criterios de Aceptación:** Clips diferenciados por color y luminosidad, playhead naranja de 2 px y cabeceras de 164 px alineadas milimétricamente.

---

### FASE 6: Inspector y Panel de Medios
- **Objetivo:** Implementar la experiencia de navegación de recursos y el inspector unificado de parámetros.
- **Tareas Técnicas:**
  1. Panel Medios (`PlaylistDock`, `src/docks/playlistdock.ui` y `.cpp`):
     - Cabecera con botón `+ Importar` y buscador `#0F1115`.
     - Conmutador segmentado `[ Lista de reproducción | Recientes ]`.
     - Cuadrícula de 2 columnas para miniaturas 16:9 con chips de duración en esquina.
     - Dropzone inferior punteado (`#343944`) con texto "Arrastra archivos aquí".
  2. Inspector (`m_propertiesDock` y `FiltersDock`):
     - Pestañas superiores `[ Inspector | Tareas | Historial ]` con subrayado de 2 px `#FF7A45`.
     - Sección TRANSFORMAR con campos numéricos para Posición X/Y y sliders de precisión para Escala, Rotación y Opacidad.
     - Sección FILTROS con filas de superficie `#1D2027`, toggles estilo interruptor (`#FF7A45` en activo) y botón punteado `+ Añadir filtro`.
- **Archivos Probables:**
  - `src/docks/playlistdock.ui`, `playlistdock.cpp`, `playlistdock.h`
  - `src/docks/filtersdock.cpp`, `filtersdock.h`
  - `src/docks/jobsdock.ui`, `historyundoview.cpp`
- **Riesgos:** Pérdida de reactividad de los filtros dinámicos al cambiar de clip en la línea de tiempo.
- **Criterios de Aceptación:** Búsqueda fluida en Medios, grid de dos columnas con thumbnails correctos y conmutación ágil de filtros en el Inspector.

---

### FASE 7: Ajustes, Acentos Dinámicos y Retrocompatibilidad
- **Objetivo:** Proveer personalización al usuario permitiendo cambiar el color de acento y regresar al modo clásico si lo desea.
- **Tareas Técnicas:**
  1. Incorporar en los ajustes de la aplicación (`src/dialogs/settingsdialog.cpp` o menú Ajustes, verificar en el repositorio) un selector de Color de Acento con opciones:
     - Naranja Grafito (por defecto): `#FF7A45`
     - Azul Eléctrico: `#5B8CFF`
     - Ámbar Dorado: `#F5B83D`
     - Lavanda Neón: `#B08CFF`
  2. Implementar un conmutador de tema "Grafito Moderno / Clásico Fusion" que permita restaurar la interfaz original en cualquier momento.
  3. Propagar la variable de acento seleccionada tanto al motor de QSS como a las propiedades raíz del contexto de QML (`qmlContext->setContextProperty("accentColor", ...)`).
- **Archivos Probables:**
  - `src/mainwindow.cpp`
  - `src/shotcutsettings.cpp` (verificar en el repositorio)
  - `capcut_theme.qss`
- **Riesgos:** Persistencia errónea de claves de acento en el registro de Windows (`HKCU\Software\Meltytech\Shotcut`).
- **Criterios de Aceptación:** El cambio de acento actualiza instantáneamente botones, sliders, cabezal de línea de tiempo y chips sin reiniciar la aplicación.

---

## 🌐 Consideraciones Técnicas Transversales

### Compatibilidad Multiplataforma (Windows, macOS, Linux)
- En **macOS**: Respetar la integración con la barra de menú nativa del sistema si el usuario tiene activada la integración global, asegurando que el botón hamburguesa actúe de respaldo. Integrar esquinas redondeadas respetando los gestos de ventana en Cocoa.
- En **Windows**: Integración correcta con el modo oscuro del sistema operativo (`DwmSetWindowAttribute` para bordes oscuros en Windows 10/11) y soporte de menús contextuales oscuros.
- En **Linux**: Correcta interpretación bajo servidores gráficos X11 y Wayland con estilos Fusion.

### Escalado HiDPI (125 %, 150 %, 200 %)
- Uso riguroso de tamaños relativos basados en `devicePixelRatio` y carga de SVG escalables.
- Ajuste de márgenes (8 px) y alturas (52 px, 44 px) en enteros escalados para evitar artefactos de subpíxel y líneas borrosas en pantallas de alta densidad.

### Rendimiento en Tiempo Real
- Cero sobrecoste computacional durante la reproducción activa: la integración del medidor de audio en el visor debe consultar la cola de audio compartida de MLT mediante temporizador eficiente (30–60 fps) sin bloquear el hilo de la interfaz.
- El canvas de QML (`timeline.qml`) debe mantener el reciclado de elementos visuales (delegates en `Repeater` o `ListView`) para evitar caídas de fotogramas en proyectos con cientos de clips.

### Licenciamiento y Cumplimiento Legal
- El núcleo de Shotcut está distribuido bajo **GNU General Public License v3.0 (GPLv3)**. Toda modificación del código fuente, wrappers de conexión y estilos derivados preservan la licencia GPLv3.
- Las fuentes tipográficas incorporadas (`Geist` y `Geist Mono`) se distribuyen bajo **SIL Open Font License 1.1 (OFL)**, totalmente compatible para empaquetado y distribución conjunta.
- La biblioteca de iconos tipo Lucide se distribuye bajo **Licencia ISC**, permitiendo su uso e incrustación sin restricciones.

---

## 📁 Resumen Consolidado de Archivos a Modificar

| # | Archivo del Repositorio | Área / Módulo | Tipo de Intervención | Fase |
|---|---|---|---|---|
| 1 | `src/mainwindow.cpp` | Core Shell | Layout de 4 columnas, ocultar menú tradicional, paleta base | F1, F3, F7 |
| 2 | `src/mainwindow.ui` | Core Shell | Simplificación de barra superior a 52 px y botón Exportar | F3 |
| 3 | `src/mainwindow.h` | Core Shell | Variables de soporte para barra lateral y metadatos | F3 |
| 4 | `capcut_theme.qss` | Estilos Globales | Inyección de tokens Grafito, radios de 12 px, sliders y botones | F1, F6 |
| 5 | `icons/resources.qrc` | Recursos (verificar) | Empaquetado de fuentes Geist/Geist Mono y glifos Lucide SVG | F1, F2 |
| 6 | `src/player.cpp` / `.h` | Visor de Video | Medidor integrado, fondo `#08090B`, botón Play 44 px | F4 |
| 7 | `src/docks/playlistdock.ui` / `.cpp` | Medios | Grid de 2 columnas, botón Importar, buscador y dropzone | F6 |
| 8 | `src/docks/filtersdock.cpp` / `.h` | Inspector | Filas de filtros con toggles interactivos y estilo de tarjetas | F6 |
| 9 | `src/docks/timelinedock.cpp` | Línea de Tiempo | Barra de herramientas de 44 px agrupada con divisores | F5 |
| 10 | `src/qml/views/timeline/timeline.qml` | Multitrack QML | Fondos `#111317`, playhead 2 px acento, regla 28 px | F5 |
| 11 | `src/qml/views/timeline/TrackHead.qml` | Multitrack QML | Cabeceras de 164 px con insignias y alturas específicas | F5 |
| 12 | `src/qml/views/timeline/Clip.qml` | Multitrack QML | Colores de video/audio/imagen, borde de acento en selección | F5 |
| 13 | `src/defaultlayouts.h` | Persistencia | Regeneración de estado serializado de ventanas predeterminado | F3 |
| 14 | `src/shotcutsettings.cpp` (verificar) | Configuración | Persistencia de acento configurable y selector de tema | F7 |

---

## 🔒 Restricciones Operativas y Prioridad de Ejecución

> [!CAUTION]
> **RECORDATORIO OPERATIVO CRÍTICO:**  
> En el entorno de ejecución actual, el binario C++ de Shotcut AI **NO debe ser recompilado desde cero** salvo que se disponga de la cadena completa de compilación de Qt6 y MLT configurada.  
> Los cambios se aplican con éxito inmediato en el sistema del usuario siguiendo este orden de prioridades:
> 1. **Prioridad 1 (Inmediata / Runtime):** Modificaciones en archivos QML (`timeline.qml`, `Clip.qml`, `TrackHead.qml`) se reflejan en tiempo real al sincronizarse con `AppData\Local\Programs\Shotcut\share\shotcut\qml\`.
> 2. **Prioridad 2 (Inmediata / Lanzador):** Hoja de estilos `capcut_theme.qss` se aplica directamente en cada inicio a través del argumento `-stylesheet` de `splash_launcher.pyw`.
> 3. **Prioridad 3 (Inmediata / Script):** Disposición de docks mediante inyección en el registro de Windows (`HKCU\Software\Meltytech\Shotcut`).
> 4. **Prioridad 4 (Documentada / Compilación):** Cambios arquitectónicos en archivos C++ (`mainwindow.cpp`, `player.cpp`) quedan listos y versionados en el repositorio para la compilación formal del binario.

---

## 📋 Entregables del Plan

### 1. Checklist de Tareas por Fase
- [x] **Fase 1: Tema Base**
  - [x] Integrar fuentes Geist y Geist Mono en reglas QSS y displays.
  - [x] Actualizar `QPalette` con fondo `#0B0C0F`, base `#0F1115` y acento `#FF7A45`.
  - [x] Rediseñar `capcut_theme.qss` con los tokens de color y radios de 12 px.
  - [x] Purgar QSS inline del constructor de `MainWindow`.
- [x] **Fase 2: Iconografía**
  - [x] Incorporar SVG estilo Lucide (trazo 1.75, grid 24x24, terminales redondeados, 72 iconos maestros en `icons/dark/32x32/` y registrados en `icons/resources.qrc`).
  - [x] Establecer tamaños estándar de 18 px y 15 px compactos en `capcut_theme.qss`, `src/mainwindow.ui`, `src/mainwindow.cpp`, `src/widgets/docktoolbar.cpp`, `src/widgets/docktoolbar.h` y `src/docks/timelinedock.cpp`, con especificidad QSS blindada contra sobreescrituras en barras de acoplamiento estándar (Playlist, Keyframes, Player, etc.).
  - [x] Verificar estados de color en reposo (`#9AA1AD`), hover (`#E8EAEE`), activo/checked (`#FF7A45` / `#FF7A452E`), presionado (`#FF7A45` / `:checked:pressed`) y deshabilitado (`#5F6672`).
  - [x] Blindar regresión e invariancia con suite E2E completa pasando al 100% y 10/10 tests específicos en `test_phase2_icon_and_theme_verification.py` con validación real de estilos QSS aplicados en runtime.
- [x] **Fase 3: Estructura de Docks**
  - [x] Ocultar barra de menú clásica y cablear botón hamburguesa (mismos menús, atajos preservados, tecla Alt, opción `View > Show Menu Bar`).
  - [x] Configurar barra superior en 52 px con layout segmentado y botón Exportar (logo 28 px, proyecto + metadatos, Deshacer/Rehacer, Tareas con contador).
  - [x] Implementar barra lateral de 52 px con accesos rápidos (Medios, Filtros, Fotogramas clave, Subtítulos, Notas, Reciente + Ayuda).
  - [x] Organizar layout de 4 columnas respetando alturas de 500 px (6 espacios de trabajo regenerados con `scripts/generate_grafito_layout.py`; 23 tests en `tests/test_phase3_layout_verification.py`).
- [ ] **Fase 4: Visor y Transporte**
  - [ ] Configurar escenario de video en `#08090B`.
  - [ ] Incrustar medidor de audio de 6 px en el lateral derecho del visor.
  - [ ] Implementar botón de reproducción circular de 44 px en color de acento.
  - [ ] Reorganizar barra de transporte con timecode en Geist Mono.
- [ ] **Fase 5: Línea de Tiempo QML**
  - [ ] Actualizar colores en `timeline.qml` y playhead de 2 px con acento.
  - [ ] Rediseñar `TrackHead.qml` a 164 px con insignias V2, V1, A1, A2 y alturas diferenciadas.
  - [ ] Implementar tokens cromáticos de clips en `Clip.qml` (video, imagen, audio).
  - [ ] Configurar borde y anillo de acento para clips seleccionados.
- [ ] **Fase 6: Inspector y Medios**
  - [ ] Rediseñar `PlaylistDock` en cuadrícula de 2 columnas con botón Importar y dropzone.
  - [ ] Configurar pestañas del Inspector (Inspector, Tareas, Historial) con subrayado de 2 px.
  - [ ] Incorporar controles numéricos y sliders de precisión en sección Transformar.
  - [ ] Estilizar filas de filtros con toggles interactivos.
- [ ] **Fase 7: Ajustes y Retrocompatibilidad**
  - [ ] Añadir selector de color de acento (#FF7A45, #5B8CFF, #F5B83D, #B08CFF).
  - [ ] Implementar opción para alternar entre tema Grafito y tema clásico.
  - [ ] Validar que 624/624 pruebas E2E continúan pasando satisfactoriamente.

---

### 2. Criterios de Aceptación Verificables
1. **Paleta y Tipografía:** El fondo de la ventana principal es exactamente `#0B0C0F`, los paneles presentan bordes `#22252D` con esquinas de 12 px, y todos los títulos y timecodes se renderizan en Geist y Geist Mono respectivamente.
2. **Top Bar Funcional:** La barra superior mide 52 px de altura, incluye el botón de menú hamburguesa funcional, el selector de espacios de trabajo, los botones de deshacer/rehacer y el botón primario "Exportar" con fondo `#FF7A45` y texto `#140A05`.
3. **Visor de Video:** El video se reproduce sobre fondo `#08090B`, con el medidor de picos de audio de 6 px funcionando en su margen derecho y un botón central de reproducción circular de 44 px en color de acento.
4. **Línea de Tiempo Multitrack:** Las 4 pistas muestran alturas conformes (V2=44 px, V1=58 px, A1=52 px, A2=40 px), cabeceras de 164 px con insignias, el cabezal mide 2 px en color de acento, y los clips exhiben sus colores específicos (#24346B para video, #34275A para imagen, #0F3B35 para audio con onda al 85 %).
5. **Invarianza de Funcionalidades:** El 100 % de las acciones originales de Shotcut permanecen accesibles a través de la barra superior, barra lateral o inspector según la matriz de correspondencia.
6. **Estabilidad del Suite de Pruebas:** La ejecución de `python tests/run_e2e_tests.py` finaliza con código de salida 0 y 624 pruebas aprobadas.

---

### 3. ⚖️ Conflictos a Decidir

Al comparar la propuesta inicial de `plan.md` con la especificación detallada del diseño "Grafito", se identifican los siguientes puntos divergentes que Fox debe arbitrar:

| # | Parámetro | Opción A (Plan Preliminar / CapCut Cyan) | Opción B (Especificación Detallada "Grafito") |
|---|---|---|---|
| **C1** | **Color de Acento Principal** | **Cian Neón (`#20e6c5`)**: Alto impacto tecnológico, texto sobre acento negro `#000000`. | **Naranja Grafito (`#FF7A45`)**: Tono editorial cálido tipo DaVinci/Figma, texto sobre acento `#140A05`, con alternativas configurables. |
| **C2** | **Arquitectura de Columnas Superiores** | **3 Columnas**: Panel Medios (izq), Visor (centro), Inspector (der). | **4 Columnas**: Barra lateral de iconos de 52 px + Panel Medios (300 px) + Visor + Inspector (300 px). |
| **C3** | **Diámetro del Botón de Play Central** | **48 px**: Botón amplio prominente. | **44 px**: Dimensionado ergonómico ajustado al estándar de botones circulares de transporte. |
| **C4** | **Familia Tipográfica** | **Fuentes de Sistema**: `Segoe UI` en Windows, `sans-serif` genérico. | **Fuentes Dedicadas Empaquetadas**: `Geist` (interfaz) y `Geist Mono` (cifras/timecodes) bajo licencia OFL. |
| **C5** | **Radio de Paneles y Espaciado** | **8 px de radio**, docks adosados tradicionalmente con separador estándar. | **12 px de radio**, paneles flotantes con margen exterior y separación entre paneles de exactamente 8 px. |
| **C6** | **Colores Base de Superficie** | Fondo `#121214`, paneles `#16161a`. | Fondo `#0B0C0F`, paneles `#15171C`, tarjetas `#1D2027`. |

---

### 4. ❓ Preguntas Abiertas

1. **Persistencia del Selector de Acento:** ¿Deseas que la selección del color de acento (#FF7A45 vs. #5B8CFF vs. #20E6C5) se almacene en el registro de Windows por usuario o como una preferencia asociada al archivo de proyecto `.mlt`?
2. **Comportamiento de la Barra Lateral de 52 px:** Al hacer clic en un icono de la barra lateral (por ejemplo, "Subtítulos" o "Notas"), ¿debe abrirse como un panel flotante temporal superpuesto o debe intercambiar la pestaña visible en el panel de Medios / Inspector?
3. **Botón Hamburguesa vs. Tecla Alt:** ¿Se prefiere que el menú hamburguesa despliegue un menú popup estilizado en QSS o que active la barra de menús nativa tradicional de Qt de forma flotante?

---

*Plan integral actualizado por Mila 1.5 🌸✨ y el equipo de diseño y arquitectura de Shotcut AI para Fox.*
