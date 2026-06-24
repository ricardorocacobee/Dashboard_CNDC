# Extractor y Dashboard CNDC

Proyecto local para descargar, normalizar y visualizar datos publicos de Operacion en Tiempo Real del CNDC Bolivia.

La fase 1 genera archivos crudos y CSV normalizados. La fase 2 agrega paginas web locales independientes con tres graficas: generacion, demanda y frecuencia del SIN. La fase actual agrega un dashboard rotativo final que embebe esas tres paginas y dos pantallas SCADA en un iframe a pantalla completa. Esta entrega no modifica el dashboard productivo COBEE ni toca la configuracion SCADA.

## Instalacion

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Ejecutar extractor

Usa automaticamente la ultima fecha `TIEMPO_REAL` publicada por `/rt/fechas`:

```powershell
python -m cndc_extractor
```

Fecha manual:

```powershell
python -m cndc_extractor --fecha 2026-06-18
```

Modo HAR:

```powershell
python -m cndc_extractor --har ".\OPERACIÓN_EN_TIEMPO_REAL.har"
```

## Ejecutar dashboard

```powershell
python -m cndc_dashboard
```

Abrir navegador:

```text
http://127.0.0.1:8000/dashboard.html
http://127.0.0.1:8000/generacion.html
http://127.0.0.1:8000/demanda.html
http://127.0.0.1:8000/frecuencia.html
```

Prueba en red local:

```powershell
python -m cndc_dashboard --host 0.0.0.0 --port 8000
```

Detener el servidor:

```text
Ctrl + C
```

## Fase 1

El extractor:

- consulta `/rt/fechas`;
- selecciona la ultima fecha `TIEMPO_REAL`;
- descarga generacion de la fecha seleccionada, dia anterior y siete dias antes;
- descarga demanda;
- descarga frecuencia reciente;
- guarda JSON crudo;
- genera CSV normalizados;
- genera `metadata.json`, `resumen_validacion.txt` y logs rotativos.

Salida:

```text
data/
|-- raw/YYYY-MM-DD/
|-- normalized/YYYY-MM-DD/
`-- ultima_extraccion.json
```

El valor `-1` se interpreta como dato ausente y se escribe como celda vacia. No se convierte a cero.

`Total SIN` se calcula solo con series departamentales validas y excluye `Prev.SCZ`.

## Correccion de hora de frecuencia

El endpoint `/rt/frecuencia/historial` del CNDC entrega timestamps como `2026-06-18T10:08:55Z`, pero en este contexto ese `Z` representa la hora de reloj local mostrada por el CNDC, no UTC real.

Por eso el extractor y el dashboard interpretan esos timestamps como hora local de Bolivia sin desplazar el reloj:

```text
2026-06-18T10:08:55Z -> 2026-06-18T10:08:55-04:00
```

Si un timestamp viene sin zona, tambien se asigna `America/La_Paz` sin desplazamiento. Si viene con offset explicito diferente de `Z`, se respeta el offset y se convierte normalmente a Bolivia.

## Fase 2

El dashboard usa:

- FastAPI;
- Jinja2;
- HTML, CSS y JavaScript puro;
- Plotly.js servido localmente desde `static/vendor/plotly.min.js`;
- servicios y normalizadores existentes del extractor.

La pagina no consulta directamente la API del CNDC desde el navegador. Todas las solicitudes pasan por FastAPI local.

Endpoints:

```text
GET  /                         -> redirige a /dashboard.html
GET  /dashboard.html
GET  /generacion.html
GET  /demanda.html
GET  /frecuencia.html
GET  /api/dashboard/config
GET  /api/status
GET  /api/fechas/latest
GET  /api/generacion?fecha=YYYY-MM-DD
GET  /api/demanda?fecha=YYYY-MM-DD
GET  /api/frecuencia?registros=360
POST /api/refresh
```

La interfaz incluye:

- selector de fecha para generacion y demanda;
- actualizacion manual;
- tres paginas HTML independientes, sin pestanas ocultas;
- actualizacion automatica de frecuencia cada 60 segundos;
- actualizacion automatica de generacion y demanda cada 15 minutos cuando se usa la fecha `TIEMPO_REAL`;
- estados de carga, cache, error y fuente de datos;
- respaldo en memoria y lectura de CSV normalizados si la API falla.

Las paginas `generacion.html`, `demanda.html` y `frecuencia.html` estan disenadas para uso a pantalla completa o dentro de un iframe. La grafica ocupa casi todo el viewport; los metadatos inferiores son texto tecnico discreto y la fuente visible se muestra como `CNDC`.

## Dashboard rotativo final

Inicio:

```powershell
.\.venv\Scripts\Activate.ps1
python -m cndc_dashboard
```

Acceso:

```text
http://127.0.0.1:8000/dashboard.html
```

El dashboard rotativo contiene un unico iframe a pantalla completa y cambia automaticamente cada 40 segundos. El orden configurado es:

```text
Generacion
Demanda
Frecuencia
Volumenes SCADA
Informacion SCADA
```

Controles disponibles:

- anterior;
- siguiente;
- indicadores de pantalla;
- pausa/reanudar;
- flecha izquierda y flecha derecha;
- barra espaciadora.

Los controles estan en la esquina inferior derecha, se muestran al cargar, aumentan opacidad con el mouse o foco de teclado y se atenuan despues de 4 segundos sin interaccion. Si la rotacion queda pausada, permanecen visibles.

La configuracion esta centralizada en `config/settings.json`, seccion `dashboard_rotation`. Ahi se cambian:

- URLs;
- orden;
- paginas habilitadas;
- intervalo de rotacion;
- tiempo de autoocultacion;
- timeout de carga.

Las primeras tres pantallas usan rutas relativas:

```text
/generacion.html
/demanda.html
/frecuencia.html
```

Las pantallas SCADA usan actualmente:

```text
http://10.101.10.210/scadawww/indexvol.htm
http://10.101.10.210/scadawww/
```

Limitaciones:

- las paginas SCADA requieren acceso a la red interna;
- la prueba se ejecuta localmente;
- todavia no se ha instalado en el servidor productivo;
- si en el futuro el dashboard se publica mediante HTTPS, las paginas SCADA HTTP podrian ser bloqueadas como contenido mixto y seria necesario revisar la infraestructura.

## Graficas

Generacion:

- Previsto;
- Total;
- Termoelectrica;
- Hidroelectrica;
- Solar;
- Eolica;
- Renovable;
- Total Ayer;
- Total Hace 7 dias.

Demanda:

- Total SIN;
- Santa Cruz;
- La Paz;
- Cochabamba;
- Potosi;
- Oruro;
- Tarija;
- Chuquisaca;
- Beni.

Frecuencia:

- curva real;
- referencias 49.75 Hz, 50.00 Hz y 50.25 Hz;
- ultima frecuencia, hora y estado.

## Pruebas

```powershell
python -m pytest -v
python -m ruff check .
```

## Problemas frecuentes

- Si `python -m cndc_dashboard` no inicia, active `.venv` e instale dependencias.
- Si la API del CNDC falla, el dashboard intenta usar cache en memoria o CSV locales.
- Si no aparece Plotly, elimine `src/cndc_dashboard/static/vendor/plotly.min.js` y reinicie; se regenera automaticamente.
- Si una fecha historica no tiene datos, revise que existan datos publicados por CNDC para esa fecha.
