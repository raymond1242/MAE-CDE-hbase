# Uso de IA generativa en la Práctica 2

**Curso:** Ciencia de Datos Escalable · **Autor:** Raymond Negron \
**Repositorio:** https://github.com/raymond1242/MAE-CDE-hbase

## 1. Declaración

| Elemento | Detalle |
|---|---|
| Herramienta | Claude Code (Anthropic), modelo Claude Opus 5.5, como extensión de VS Code sobre este repositorio |
| Fecha | 23 y 24 de octubre de 2026, en una sola sesión de trabajo |
| Mensajes del estudiante | 12, transcritos en la sección 3 |

**Lo que hizo la IA:**

- Propuso la estructura del repositorio y el dataset sintético.
- Escribió el código en Python y los scripts de HBase, las pruebas unitarias, la guía para crear el clúster
  EMR y el paso a paso.
- Probó el flujo completo en un HBase 2.6.4 local (Docker) antes de usar EMR.
- Diagnosticó un error de red de AWS.
- Redactó el informe (explicaciones, interpretación y análisis conceptual) a partir de los resultados
  reales.
- Generó los PDF y organizó los commits.

**Lo que hizo el estudiante:**

- Definió el alcance y las restricciones: un clúster mínimo, el idioma del repositorio, el uso de la
  consola de AWS y de una cuenta personal.
- Creó el clúster EMR en su cuenta de AWS.
- Ejecutó en el clúster todos los pasos: creación de la tabla, carga, verificación, consultas y análisis.
  Compartió las salidas.
- Revisó el informe y pidió ajustes: simplificar el análisis conceptual y mejorar el README.
- Decidió qué entregar.

**Cómo se verificaron los resultados:**

- Los indicadores del informe provienen de la ejecución en el clúster EMR `j-00430072CCSGFQ8WWNLK`.
- Se compararon dos métodos de extracción independientes (Thrift y la exportación del shell de HBase) y
  dieron resultados idénticos.
- Los datos leídos de HBase coinciden con el dataset cargado.

## 2. Resumen de la sesión

| # | Fase | Propósito del mensaje |
|---|---|---|
| 1 | Planificación | Plantear la tarea completa y pedir estructura, dataset, guía de EMR y código |
| 2 | Planificación | Limitar el clúster EMR a lo mínimo necesario |
| 3 | Planificación | Definir el idioma: repositorio en inglés, respuestas en español |
| 4 | Clúster EMR | Resolver el error de VPC/subnet y adaptar la guía a la consola y a una cuenta personal |
| 5 | Clúster EMR | Validar que el clúster quedó listo con las salidas de verificación |
| 6 | Ejecución | Registrar la carga de datos y pedir una explicación de lo realizado |
| 7 | Ejecución | Entregar el ID del clúster y pedir la revisión de los resultados |
| 8 | Versionado | Organizar los commits por grupos de archivos |
| 9 | Informe | Simplificar el análisis conceptual |
| 10 | Entrega | Definir qué archivos subir y revisar el README |
| 11 | Entrega | Generar el PDF del informe y decidir sobre el zip |
| 12 | Entrega | Documentar el uso de IA generativa (este archivo) |

## 3. Mensajes utilizados

Los mensajes se transcriben textualmente, con sus erratas. Las capturas de pantalla y las salidas de
terminal que acompañaban algunos mensajes se describen entre corchetes.

### Mensaje 1: planteamiento de la tarea

> *[Adjunto: enunciado de la práctica en PDF]*
>
> Necesito que me ayudes a completar esta tarea, desde:
>
> - la creación del EMR en aws, la creación de la tabla (pienso que para esto primero debemos de ecoger o crear un dataset que cumpla con las columnas que vamos a analizar y requiere la tarea)
> - los comandos que se usaran en hbase para responder a las preguntas de la actividad 2
> - Indica que se puede utilizar python para procesar los registros, pienso que podemos usar python para tener documentado en codigo como hacer ese proceso y de paso explicamos la conexión, y de paso responder a la sección de analisis conceptual, porque en entregables exige codigo utilizado, la tabla de resultado de cada indicador, la interpretación y respuestas.
>
> Entonces, para lograr todo esto he creado un repositorio en donde te encuentras para tener todo versionado y documentado para que pueda ser reproducible luego, por tanto crea un readme explicando lo que hace esste repo, y luego dame una estructura sobre el cual podemos trabajar, y la fase final sería que implementes todo y me des un paso a paso de qué hacer para completar esta tarea, que a su vez será registrado (los resultado) en cuanto vayamos completando los pasos, que formato de documento es el adecuado para entregar tablas de resultados (para eso imagino que esta bien un CSV), para las respuestas e interpretación creo que un .md esta bien. Pero considera tambien que debemos tener un dataset (agarrar uno o crear uno cuál me recomiendas) para usarlo y problar la tabla. Considera tambien una guía para mi sobre como crear el EMR en aws con lo que se necesite para conectarlo con nuestros escripts de python \
> Te adjunté el pdf de la tarea para los detalles

**Resultado:** se creó el repositorio completo:

- Dataset sintético reproducible de 300 empleados, con problemas de calidad incluidos a propósito.
- Scripts de HBase para las actividades A y B.
- Código Python de carga, extracción (happybase vía Thrift, con la exportación del shell como respaldo)
  y cálculo de indicadores.
- Pruebas unitarias, guía de EMR, paso a paso y plantilla del informe.

Todo se probó contra HBase 2.6.4 en Docker.

### Mensaje 2: clúster mínimo

> Usemos un EMR básico y necesario para completar las respuestas, solo es una tarea que no requiere gran procesamiento y performance

**Resultado:** se definió un clúster de 1 nodo primario y 1 nodo core `m5.xlarge`, sin escalado y con
terminación automática por inactividad.

### Mensaje 3: idioma del repositorio

> Y finalmente, que sea en ingles la estructura del repo, solo las respuestas deben ser en español, todo lo demas en ingles, la tabla, campos y registros, todo en ingles, excepto las preguntas de los resultados

**Resultado:** el código, la documentación, la tabla, los campos y los registros quedaron en inglés. El
informe con las respuestas quedó en español.

### Mensaje 4: error de red al crear el clúster

> Respecto a la guia de @docs/01_emr_setup.md \
> he tenido este error cuando se creo el cluster: \
> The VPC/subnet configuration was invalid: No route to any external sources detected in Route Table for Subnet: subnet-037a1a69581f3f5ef for VPC: vpc-0cd16ba4caaa9498b
>
> para precisar, yo voy por la opcion A de usar aws console, solo considera esa opcion, y recuerda que lo estoy haciendo con mi cuenta personal, entonces corrige o modificar ese doc con esas espceficiaciones, y puedes detallas un poco mas quizá fallé en algo

**Resultado:** el diagnóstico fue que la subnet elegida no tenía ruta a un internet gateway. La guía se
reescribió solo para la consola y una cuenta personal, con un paso previo para verificar la VPC por
defecto y una subnet pública. Se eliminaron los scripts de la AWS CLI.

### Mensaje 5: verificación del clúster

> ok perfecto, te comparto todo lo que corrí y respuestas del paso 7 para que actualices si hay algo segun esos datos, y luego dime que mas debo hacer y si ya esta seteado el cluster
>
> *[Captura de pantalla de la consola de EMR: un intento previo, hbase-practice-2, terminado con errores.]* \
> *[Salida de terminal: conexión SSH al nodo primario; "HBase 2.6.4-amzn-2"; "1 active master, 0 backup masters, 1 servers, 0 dead"; servidor Thrift escuchando en el puerto 9090.]*

**Resultado:** se confirmó que el clúster estaba listo. Además se detectaron tres puntos:

- La terminación automática no está soportada con HBase, así que se recomendó subir el tiempo de
  inactividad a 3 horas y terminar el clúster manualmente.
- Había un nodo Task de más en el intento fallido.
- El comando para copiar el repositorio al clúster debía corregirse.

### Mensaje 6: carga de datos y explicación

> te comparto los outputs, que mas debo hacer? y de paso puedes explicarme lo que hicimos pls
>
> *[Salida de terminal: copia del repositorio al nodo primario, setup_primary.sh ("Setup complete"), creación de la tabla emp y carga "300 rows and 1187 cells written to 'emp' via Thrift".]*

**Resultado:** se explicó la arquitectura (qué corre en cada nodo) y cada paso realizado. Se entregaron
los comandos de los pasos siguientes con los valores esperados, y se corrigió el comando para traer los
resultados al laptop.

### Mensaje 7: resultados de la ejecución en EMR

> id del cluster es j-00430072CCSGFQ8WWNLK \
> ya aumente el tiempo de inactividad tambien
>
> y listo, ya corrí todos los comandos, puedes revisar el repo

**Resultado:** se verificaron los resultados:

- Los dos métodos de extracción dieron resultados idénticos.
- Los datos leídos de HBase coinciden con el dataset.

Después se completaron el informe (ID del clúster e interpretación de 5 a 10 líneas) y el registro de
ejecución.

### Mensaje 8: commits

> Puedes hacer commit en partes de todo lo que se escribió pls, pero no hagas un solo commit de todo, sino en partes según convenga agrupar los files

**Resultado:** 12 commits agrupados por función: base, datos, HBase, carga y lectura, indicadores,
generador del informe, pruebas, infraestructura, entorno local, documentación, resultados e informe
final.

### Mensaje 9: simplificar el análisis conceptual

> ok perfect, sobre el report: \
> @deliverable/REPORT.md \
> en la sseccion 6 sobre analisis conceptual, puede concretizarlo un poco, parece muy verboso y da informacion extra adicional que creo que podemos omitir, por ejemplos: \
> WAL y MemStore para las escrituras, HFiles sobre HDFS
>
> y se aleja de la respuesta como tal, puede revisar eso pls

**Resultado:** la sección 6 se redujo a menos de la mitad. Cada respuesta va directo a la pregunta y se
eliminaron los detalles internos de HBase y el código de ejemplo de Spark.

### Mensaje 10: qué entregar y revisión del README

> ok listo, ya esta, ahora finalmente, dime que escripts debo subir, porque el entregable pide codigo, y los reportes, sobre el reporte pienso que puedo enviar el @deliverable/REPORT.md#1-302
>
> pero indicame que dile, pienso subir todo lo del source y hbase
>
> puede revisar si el readme esta bien, si es concreto y preciso tambien porque subiré eso, tambien menciona en el readme el enlace al repo porque seguro el profesor entrará al repo para mayor detalle

**Resultado:** el README se reescribió con el enlace al repositorio, un resumen de resultados y el mapa de
entregables. También se agregó el enlace al repositorio en el informe y se recomendó qué archivos subir.

### Mensaje 11: PDF y zip

> puedes generar el pdf pls para subirlo, y respecto al entregable me recomiendas subir el zip?

**Resultado:** se generó `REPORT.pdf`, con tablas sin cortes y enlaces a GitHub. También se generó un zip
con el código, el dataset y los resultados de EMR para acompañar el PDF.

### Mensaje 12: registro de uso de IA

> ok perfecto, finalmente, como usamos ia generativa para realizar esta tarea, en deliverables crea un .md sobre los mensaje que utilicé para lograr esta tarea, usa los mensjaes de esta sesión, y colocalos en un .md de deliveable, y genera un pdf de eso tambien

**Resultado:** este documento (`deliverable/AI_USAGE.md`) y su versión en PDF.
