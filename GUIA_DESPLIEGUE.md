# 🚀 **Guía Completa: API LH Tarja - De Cloud SQL a Cloud Run**

## 📋 **Resumen del Proyecto**

Esta guía documenta el proceso completo de configuración y despliegue de la API LH Tarja, desde la configuración de la base de datos MySQL en Google Cloud SQL hasta el despliegue automático en Google Cloud Run con CI/CD.

---

## 🎯 **Objetivos Alcanzados**

✅ **Conexión segura a Cloud SQL**  
✅ **API Flask con autenticación JWT**  
✅ **Despliegue automático en Cloud Run**  
✅ **CI/CD con GitHub Actions**  
✅ **CORS configurado para Flutter**  
✅ **Logs y monitoreo implementados**

---

## 🏗️ **Arquitectura Final**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flutter App   │    │   Cloud Run     │    │   Cloud SQL     │
│                 │◄──►│   API Flask     │◄──►│   MySQL DB      │
│   (Frontend)    │    │   (Backend)     │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ GitHub Actions  │
                       │   (CI/CD)       │
                       └─────────────────┘
```

---

## 📚 **Índice del Proceso**

1. **[Configuración Inicial](#1-configuración-inicial)**
2. **[Configuración de Cloud SQL](#2-configuración-de-cloud-sql)**
3. **[Desarrollo de la API Flask](#3-desarrollo-de-la-api-flask)**
4. **[Configuración de Conexión a BD](#4-configuración-de-conexión-a-bd)**
5. **[Despliegue en Cloud Run](#5-despliegue-en-cloud-run)**
6. **[Configuración de CI/CD](#6-configuración-de-cicd)**
7. **[Pruebas y Validación](#7-pruebas-y-validación)**
8. **[Integración con Flutter](#8-integración-con-flutter)**

---

## 1. **Configuración Inicial**

### **1.1 Preparación del Entorno**

**Requisitos previos:**
- Cuenta de Google Cloud Platform
- Proyecto GCP configurado
- Git y GitHub configurados
- Python 3.12 instalado

**Comandos iniciales:**
```bash
# Crear directorio del proyecto
mkdir api_lh_tarja
cd api_lh_tarja

# Inicializar repositorio Git
git init
git remote add origin https://github.com/tu-usuario/api_lh_tarja.git

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
```

### **1.2 Estructura del Proyecto**

```
api_lh_tarja/
├── app.py                 # Aplicación principal Flask
├── config.py             # Configuración del sistema
├── requirements.txt      # Dependencias Python
├── Dockerfile           # Configuración del contenedor
├── .env                 # Variables de entorno (local)
├── .github/workflows/   # CI/CD con GitHub Actions
│   └── deploy.yaml
├── blueprints/          # Módulos de la API
│   ├── auth.py         # Autenticación JWT
│   ├── actividades.py  # Gestión de actividades
│   ├── usuarios.py     # Gestión de usuarios
│   ├── opciones.py     # Opciones del sistema
│   ├── rendimientos.py # Rendimientos
│   ├── trabajadores.py # Trabajadores
│   ├── contratistas.py # Contratistas
│   ├── colaboradores.py # Colaboradores
│   ├── permisos.py     # Permisos
│   ├── tarjas.py       # Tarjas
│   └── rendimientopropio.py # Rendimientos propios
└── utils/
    ├── db.py           # Conexión a base de datos
    └── validar_rut.py  # Validación de RUT chileno
```

---

## 2. **Configuración de Cloud SQL**

### **2.1 Crear Instancia de Cloud SQL**

**En Google Cloud Console:**

1. **Ir a SQL en la consola de GCP**
2. **Crear instancia:**
   - **Nombre:** `lahornilla-db`
   - **Región:** `us-central1`
   - **Tipo:** MySQL 8.0
   - **Configuración:** `db-n1-standard-1` (1 vCPU, 3.75 GB)
   - **Almacenamiento:** 10 GB SSD

**Comando gcloud:**
```bash
gcloud sql instances create lahornilla-db \
    --database-version=MYSQL_8_0 \
    --tier=db-n1-standard-1 \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB \
    --root-password=tu-password-root
```

### **2.2 Configurar Base de Datos**

**Crear base de datos:**
```sql
CREATE DATABASE lahornilla_base_normalizada;
```

**Crear usuario de aplicación:**
```sql
CREATE USER 'UserApp'@'%' IDENTIFIED BY '&8y7c()tu9t/+,6`';
GRANT ALL PRIVILEGES ON lahornilla_base_normalizada.* TO 'UserApp'@'%';
FLUSH PRIVILEGES;
```

### **2.3 Configurar Conexión Segura**

**Habilitar Cloud SQL Admin API:**
```bash
gcloud services enable sqladmin.googleapis.com
```

**Configurar red autorizada (para desarrollo local):**
```bash
gcloud sql instances patch lahornilla-db \
    --authorized-networks=0.0.0.0/0
```

---

## 3. **Desarrollo de la API Flask**

### **3.1 Instalación de Dependencias**

**requirements.txt:**
```
Flask==3.1.0
Flask-Cors==5.0.1
PyJWT==2.10.1
bcrypt==4.3.0
mysql-connector-python==9.2.0
gunicorn==22.0.0
flask-jwt-extended==4.7.1
python-dotenv==1.0.1
```

**Instalar dependencias:**
```bash
pip install -r requirements.txt
```

### **3.2 Configuración de la Aplicación**

**config.py:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Inicio01*')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'Inicio01*')
    
    # Configuración de base de datos
    DATABASE_URL = os.getenv('DATABASE_URL')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'UserApp')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '&8y7c()tu9t/+,6`')
    DB_NAME = os.getenv('DB_NAME', 'lahornilla_base_normalizada')
    
    # Configuración de Cloud SQL
    GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'gestion-la-hornilla')
    CLOUD_SQL_CONNECTION_NAME = os.getenv('CLOUD_SQL_CONNECTION_NAME', 'gestion-la-hornilla:us-central1:lahornilla-db')
```

### **3.3 Estructura de Blueprints**

**Cada módulo se organiza en blueprints:**
- `auth.py` - Autenticación JWT
- `actividades.py` - CRUD de actividades
- `usuarios.py` - Gestión de usuarios
- `opciones.py` - Opciones del sistema
- `rendimientos.py` - Gestión de rendimientos
- `trabajadores.py` - CRUD de trabajadores
- `contratistas.py` - CRUD de contratistas
- `colaboradores.py` - CRUD de colaboradores
- `permisos.py` - Gestión de permisos

---

## 4. **Configuración de Conexión a BD**

### **4.1 Conexión Local con Cloud SQL Proxy**

**Instalar Cloud SQL Proxy:**
```bash
# Descargar Cloud SQL Proxy
curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64

# En Windows, descargar desde:
# https://dl.google.com/cloudsql/cloud_sql_proxy_x64.exe
```

**Conectar a la instancia:**
```bash
# Obtener información de conexión
gcloud sql instances describe lahornilla-db --format="value(connectionName)"

# Ejecutar proxy
cloud_sql_proxy -instances=gestion-la-hornilla:us-central1:lahornilla-db=tcp:3306
```

### **4.2 Configuración de Conexión en Código**

**utils/db.py:**
```python
import mysql.connector
import re
import logging
from config import Config

logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    try:
        # Si estamos en Cloud Run, usar DATABASE_URL
        if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
            return parse_database_url(Config.DATABASE_URL)
        
        # Conexión local con Cloud SQL Proxy
        connection_params = {
            'host': Config.DB_HOST,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'port': 3306
        }
        
        logger.info(f"🔌 Conectando a BD local: {Config.DB_HOST}")
        return mysql.connector.connect(**connection_params)
        
    except Exception as e:
        logger.error(f"❌ Error conectando a BD: {str(e)}")
        raise

def parse_database_url(url):
    """Parsear DATABASE_URL para Cloud SQL"""
    try:
        # Patrón para DATABASE_URL de Cloud SQL
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^/]+)/([^?]+)(?:\?unix_socket=([^/]+)/([^/]+/[^/]+/[^/]+))?'
        match = re.match(pattern, url)
        
        if match:
            user, password, host, database, _, instance = match.groups()
            
            if instance:  # Cloud SQL con unix_socket
                logger.info(f"🔌 Conectando a Cloud SQL: {instance}")
                return mysql.connector.connect(
                    user=user,
                    password=password,
                    database=database,
                    unix_socket=f'/cloudsql/{instance}'
                )
            else:  # Conexión TCP normal
                return mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=3306
                )
        else:
            raise ValueError("Formato de DATABASE_URL inválido")
            
    except Exception as e:
        logger.error(f"❌ Error parseando DATABASE_URL: {str(e)}")
        raise
```

### **4.3 Variables de Entorno**

**.env (desarrollo local):**
```env
DEBUG=True
DB_USER=UserApp
DB_PASSWORD=&8y7c()tu9t/+,6`
DB_NAME=lahornilla_base_normalizada
GOOGLE_CLOUD_PROJECT=gestion-la-hornilla
CLOUD_SQL_CONNECTION_NAME=gestion-la-hornilla:us-central1:lahornilla-db
SECRET_KEY=Inicio01*
JWT_SECRET_KEY=Inicio01*
```

---

## 5. **Despliegue en Cloud Run**

### **5.1 Configuración del Dockerfile**

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Exponer puerto 8080 (requerido por Cloud Run)
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "app:app"]
```

### **5.2 Configuración de la Aplicación Flask**

**app.py:**
```python
from flask import Flask, Blueprint
from flask_jwt_extended import JWTManager
from config import Config
from flask_cors import CORS
from datetime import timedelta
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://192.168.1.52:*", "http://192.168.1.208:*", "http://192.168.1.60:*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"],
            "max_age": 3600
        }
    })

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=10)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    jwt = JWTManager(app)

    # Registrar blueprints
    from blueprints.usuarios import usuarios_bp
    from blueprints.actividades import actividades_bp
    from blueprints.rendimientos import rendimientos_bp
    from blueprints.auth import auth_bp
    from blueprints.opciones import opciones_bp
    from blueprints.trabajadores import trabajadores_bp
    from blueprints.contratistas import contratistas_bp
    from blueprints.tarjas import tarjas_bp
    from blueprints.colaboradores import colaboradores_bp
    from blueprints.permisos import permisos_bp
    from blueprints.rendimientopropio import rendimientopropio_bp

    app.register_blueprint(actividades_bp, url_prefix='/api/actividades')
    app.register_blueprint(rendimientos_bp, url_prefix='/api/rendimientos')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(contratistas_bp, url_prefix='/api/contratistas')
    app.register_blueprint(trabajadores_bp, url_prefix='/api/trabajadores')
    app.register_blueprint(opciones_bp, url_prefix="/api/opciones")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tarjas_bp, url_prefix="/api/tarjas")
    app.register_blueprint(colaboradores_bp, url_prefix='/api/colaboradores')
    app.register_blueprint(permisos_bp, url_prefix='/api/permisos')
    app.register_blueprint(rendimientopropio_bp, url_prefix='/api/rendimientopropio')
    
    # Endpoints de debug
    @app.route('/api/test-db', methods=['GET'])
    def test_database():
        try:
            from utils.db import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.close()
            conn.close()
            return {"status": "success", "message": "Conexión exitosa", "mysql_version": version[0]}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
```

### **5.3 Despliegue Manual (Primera Vez)**

**Construir y desplegar:**
```bash
# Configurar proyecto
gcloud config set project gestion-la-hornilla

# Construir imagen
gcloud builds submit --tag gcr.io/gestion-la-hornilla/api-lh-tarja

# Desplegar en Cloud Run
gcloud run deploy apilhtarja \
  --image gcr.io/gestion-la-hornilla/api-lh-tarja \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances gestion-la-hornilla:us-central1:lahornilla-db \
  --set-env-vars DATABASE_URL="mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/gestion-la-hornilla:us-central1:lahornilla-db",SECRET_KEY="Inicio01*",JWT_SECRET_KEY="Inicio01*",FLASK_ENV="production",FLASK_DEBUG="0",K_SERVICE="apilhtarja"
```

---

## 6. **Configuración de CI/CD**

### **6.1 Configuración de GitHub Actions**

**.github/workflows/deploy.yaml:**
```yaml
name: Deploy API Tarja

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repo
      uses: actions/checkout@v4

    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}

    - name: Setup gcloud
      uses: google-github-actions/setup-gcloud@v2
      with:
        project_id: gestion-la-hornilla

    - name: Build and Deploy
      run: |
        gcloud builds submit --tag gcr.io/gestion-la-hornilla/api-lh-tarja
        gcloud run deploy apilhtarja \
          --image gcr.io/gestion-la-hornilla/api-lh-tarja \
          --region us-central1 \
          --platform managed \
          --allow-unauthenticated \
          --add-cloudsql-instances gestion-la-hornilla:us-central1:lahornilla-db \
          --set-env-vars DATABASE_URL="mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/gestion-la-hornilla:us-central1:lahornilla-db",SECRET_KEY="Inicio01*",JWT_SECRET_KEY="Inicio01*",FLASK_ENV="production",FLASK_DEBUG="0",K_SERVICE="apilhtarja"
```

### **6.2 Configuración de Service Account**

**Crear Service Account:**
```bash
# Crear service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions"

# Asignar roles necesarios
gcloud projects add-iam-policy-binding gestion-la-hornilla \
    --member="serviceAccount:github-actions@gestion-la-hornilla.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding gestion-la-hornilla \
    --member="serviceAccount:github-actions@gestion-la-hornilla.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding gestion-la-hornilla \
    --member="serviceAccount:github-actions@gestion-la-hornilla.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Crear y descargar key
gcloud iam service-accounts keys create ~/key.json \
    --iam-account=github-actions@gestion-la-hornilla.iam.gserviceaccount.com
```

**Configurar en GitHub:**
1. Ir a Settings > Secrets and variables > Actions
2. Crear nuevo secret: `GCP_SA_KEY`
3. Pegar el contenido del archivo `key.json`

---

## 7. **Pruebas y Validación**

### **7.1 Pruebas Locales**

**Ejecutar API localmente:**
```bash
# Activar entorno virtual
venv\Scripts\activate

# Ejecutar Cloud SQL Proxy
cloud_sql_proxy -instances=gestion-la-hornilla:us-central1:lahornilla-db=tcp:3306

# En otra terminal, ejecutar API
python app.py
```

**Probar endpoints:**
```bash
# Test de conexión a BD
curl http://localhost:8080/api/test-db

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "mbravo", "clave": "antoemma"}'
```

### **7.2 Pruebas en Producción**

**URL de producción:** `https://apilhtarja-927498545444.us-central1.run.app`

**Probar endpoints:**
```bash
# Test de conexión
curl https://apilhtarja-927498545444.us-central1.run.app/api/test-db

# Login
curl -X POST https://apilhtarja-927498545444.us-central1.run.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "mbravo", "clave": "antoemma"}'
```

### **7.3 Monitoreo y Logs**

**Ver logs en tiempo real:**
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=apilhtarja"
```

**Ver métricas del servicio:**
```bash
gcloud run services describe apilhtarja --region=us-central1
```

---

## 8. **Integración con Flutter**

### **8.1 Configuración de Flutter**

**Actualizar URL base en Flutter:**
```dart
// En tu app Flutter
const String apiBaseUrl = 'https://apilhtarja-927498545444.us-central1.run.app';

// Configurar cliente HTTP
final httpClient = http.Client();
final headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer $token', // Token JWT
};
```

### **8.2 Ejemplo de Login en Flutter**

```dart
Future<Map<String, dynamic>> login(String usuario, String clave) async {
  try {
    final response = await http.post(
      Uri.parse('$apiBaseUrl/api/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'usuario': usuario,
        'clave': clave,
      }),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      // Guardar token JWT
      await storage.write(key: 'jwt_token', value: data['access_token']);
      return data;
    } else {
      throw Exception('Error en login');
    }
  } catch (e) {
    throw Exception('Error de conexión: $e');
  }
}
```

### **8.3 Ejemplo de Llamada Autenticada**

```dart
Future<List<dynamic>> getActividades() async {
  try {
    final token = await storage.read(key: 'jwt_token');
    
    final response = await http.get(
      Uri.parse('$apiBaseUrl/api/actividades/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Error obteniendo actividades');
    }
  } catch (e) {
    throw Exception('Error de conexión: $e');
  }
}
```

---

## 🔧 **Solución de Problemas**

### **Problema: Error de Conexión a MySQL**
**Síntomas:** `MySQL Connection Error`
**Solución:**
1. Verificar que Cloud SQL Proxy esté ejecutándose
2. Verificar credenciales en `.env`
3. Verificar que la instancia esté activa

### **Problema: Error 401 Unauthorized**
**Síntomas:** `JWT token invalid`
**Solución:**
1. Verificar que el token JWT esté incluido en headers
2. Verificar que el token no haya expirado
3. Hacer login nuevamente

### **Problema: Error de CORS**
**Síntomas:** `CORS policy blocked`
**Solución:**
1. Verificar configuración CORS en `app.py`
2. Agregar dominio de Flutter a origins permitidos

### **Problema: Error en Cloud Run**
**Síntomas:** `Service not found`
**Solución:**
1. Verificar que el servicio esté desplegado
2. Verificar variables de entorno
3. Verificar logs en Cloud Run

---

## 📊 **Métricas y Monitoreo**

### **Comandos Útiles:**

**Ver logs en tiempo real:**
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=apilhtarja"
```

**Ver métricas del servicio:**
```bash
gcloud run services describe apilhtarja --region=us-central1
```

**Escalar servicio:**
```bash
gcloud run services update apilhtarja --region=us-central1 --max-instances=10
```

**Ver logs específicos:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=apilhtarja AND severity>=ERROR" --limit=50
```

---

## ✅ **Checklist de Verificación**

### **✅ Configuración de Cloud SQL:**
- [x] Instancia MySQL creada
- [x] Base de datos creada
- [x] Usuario de aplicación creado
- [x] Permisos configurados
- [x] Cloud SQL Admin API habilitada

### **✅ Desarrollo de API:**
- [x] Estructura de blueprints creada
- [x] Autenticación JWT implementada
- [x] Conexión a BD configurada
- [x] CORS configurado
- [x] Endpoints implementados

### **✅ Despliegue en Cloud Run:**
- [x] Dockerfile creado
- [x] Imagen construida
- [x] Servicio desplegado
- [x] Variables de entorno configuradas
- [x] Conexión a Cloud SQL establecida

### **✅ CI/CD:**
- [x] GitHub Actions configurado
- [x] Service Account creado
- [x] Secrets configurados en GitHub
- [x] Despliegue automático funcionando

### **✅ Pruebas:**
- [x] Conexión a BD probada
- [x] Login funcionando
- [x] Endpoints respondiendo
- [x] Flutter conectando correctamente

---

## 🚀 **Próximos Pasos**

### **Mejoras Planificadas:**
- 🔄 **Cache Redis** - Mejorar rendimiento
- 🔄 **Rate Limiting** - Protección contra spam
- 🔄 **API Versioning** - Control de versiones
- 🔄 **Documentación Swagger** - API docs interactiva
- 🔄 **Tests Automatizados** - Cobertura de código
- 🔄 **Métricas Avanzadas** - Monitoreo detallado

### **Optimizaciones:**
- 🔄 **Connection Pooling** - Mejorar conexiones BD
- 🔄 **Compresión** - Reducir tamaño de respuestas
- 🔄 **CDN** - Acelerar contenido estático
- 🔄 **Load Balancing** - Distribuir carga

---

## 📞 **Soporte y Contacto**

### **Información de Contacto:**
- **URL de Producción:** `https://apilhtarja-927498545444.us-central1.run.app`
- **Base de Datos:** Cloud SQL MySQL
- **Región:** us-central1
- **Proyecto:** gestion-la-hornilla

### **Recursos Útiles:**
- [Google Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [JWT Documentation](https://jwt.io/)

---

## 🎉 **Conclusión**

Esta guía documenta el proceso completo de configuración y despliegue de la API LH Tarja, desde la configuración inicial de Cloud SQL hasta el despliegue automático en Cloud Run con CI/CD. El sistema está ahora completamente funcional y listo para producción.

**Estado Final:** ✅ **COMPLETADO Y FUNCIONANDO** 