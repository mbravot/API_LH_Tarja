# 🚀 API LH Tarja - Documentación Completa

## 📋 **Información General**

- **URL Base:** `https://apilhtarja-927498545444.us-central1.run.app`
- **Autenticación:** JWT Bearer Token
- **Base de Datos:** MySQL (Cloud SQL)
- **Despliegue:** Google Cloud Run

---

## 🔐 **Autenticación**

### **Login**
```http
POST /api/auth/login
Content-Type: application/json

{
  "usuario": "mbravo",
  "clave": "antoemma"
}
```

**Respuesta Exitosa:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "usuario": {
    "id": "123",
    "usuario": "mbravo",
    "correo": "mbravo@lahornilla.cl",
    "id_sucursalactiva": 103,
    "sucursal_nombre": "SANTA VICTORIA"
  }
}
```

**Uso del Token:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## 📊 **Endpoints de Sistema**

### **1. Test de Base de Datos**
```http
GET /api/test-db
```
**Respuesta:**
```json
{
  "status": "success",
  "message": "Conexión exitosa",
  "mysql_version": "8.0.36"
}
```

### **2. Configuración del Sistema**
```http
GET /api/config
```
**Respuesta:**
```json
{
  "status": "success",
  "config": {
    "DATABASE_URL": "mysql+pymysql://UserApp:...",
    "DB_HOST": "localhost",
    "DB_USER": "UserApp",
    "DB_NAME": "lahornilla_base_normalizada",
    "K_SERVICE": "apilhtarja",
    "FLASK_ENV": "production"
  }
}
```

---

## 🎯 **Endpoints de Opciones**

### **1. Opciones Principales**
```http
GET /api/opciones/
Authorization: Bearer <token>
```
**Respuesta:**
```json
{
  "labores": [
    {"id": 1, "nombre": "Poda"},
    {"id": 2, "nombre": "Riego"}
  ],
  "unidades": [
    {"id": 1, "nombre": "Hectárea"},
    {"id": 2, "nombre": "Metro"}
  ],
  "tipoCecos": [
    {"id": 1, "nombre": "Productivo"},
    {"id": 2, "nombre": "Administrativo"}
  ]
}
```

### **2. Especies**
```http
GET /api/opciones/especies
Authorization: Bearer <token>
```
**Respuesta:**
```json
[
  {
    "id": 1,
    "nombre": "Uva de Mesa",
    "caja_equivalente": 8.5
  }
]
```

### **3. Variedades por Especie**
```http
GET /api/opciones/variedades?id_especie=1
Authorization: Bearer <token>
```

### **4. Sucursales**
```http
GET /api/opciones/sucursales
Authorization: Bearer <token>
```

### **5. CECOs por Tipo**
```http
GET /api/opciones/cecos
Authorization: Bearer <token>
```

### **6. Contratistas**
```http
GET /api/opciones/contratistas
Authorization: Bearer <token>
```

### **7. Tipos de Rendimiento**
```http
GET /api/opciones/tiporendimientos
Authorization: Bearer <token>
```

### **8. Porcentajes**
```http
GET /api/opciones/porcentajes
Authorization: Bearer <token>
```

### **9. Unidades**
```http
GET /api/opciones/unidades
Authorization: Bearer <token>
```

---

## 🏗️ **Endpoints de Actividades**

### **1. Listar Actividades**
```http
GET /api/actividades/
Authorization: Bearer <token>
```

### **2. Crear Actividad**
```http
POST /api/actividades/
Authorization: Bearer <token>
Content-Type: application/json

{
  "fecha": "2025-07-22",
  "id_tipotrabajador": 1,
  "id_tiporendimiento": 1,
  "id_labor": 1,
  "id_unidad": 1,
  "id_tipoceco": 1,
  "tarifa": 15000,
  "hora_inicio": "08:00",
  "hora_fin": "17:00",
  "id_estadoactividad": 1,
  "id_contratista": null
}
```

### **3. Obtener Actividad por ID**
```http
GET /api/actividades/{actividad_id}
Authorization: Bearer <token>
```

### **4. Editar Actividad**
```http
PUT /api/actividades/{actividad_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "fecha": "2025-07-22",
  "id_tipotrabajador": 1,
  "id_tiporendimiento": 1,
  "id_labor": 1,
  "id_unidad": 1,
  "id_tipoceco": 1,
  "tarifa": 15000,
  "hora_inicio": "08:00",
  "hora_fin": "17:00",
  "id_estadoactividad": 1
}
```

### **5. Eliminar Actividad**
```http
DELETE /api/actividades/{actividad_id}
Authorization: Bearer <token>
```

---

## 📈 **Endpoints de Rendimientos**

### **1. Listar Rendimientos**
```http
GET /api/rendimientos/
Authorization: Bearer <token>
```

### **2. Crear Rendimiento**
```http
POST /api/rendimientos/
Authorization: Bearer <token>
Content-Type: application/json

{
  "id_actividad": "actividad_id",
  "cantidad": 10.5,
  "observaciones": "Rendimiento normal"
}
```

### **3. Editar Rendimiento**
```http
PUT /api/rendimientos/{rendimiento_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "id_actividad": "actividad_id",
  "cantidad": 12.0,
  "observaciones": "Rendimiento actualizado"
}
```

### **4. Eliminar Rendimiento**
```http
DELETE /api/rendimientos/{rendimiento_id}
Authorization: Bearer <token>
```

---

## 👥 **Endpoints de Usuarios**

### **1. Listar Usuarios**
```http
GET /api/usuarios/
Authorization: Bearer <token>
```

### **2. Crear Usuario**
```http
POST /api/usuarios/
Authorization: Bearer <token>
Content-Type: application/json

{
  "usuario": "nuevo_usuario",
  "correo": "usuario@lahornilla.cl",
  "clave": "password123",
  "id_sucursalactiva": 103,
  "nombre": "Juan",
"apellido_paterno": "Pérez",
"apellido_materno": "González",
  "id_estado": 1
}
```

### **3. Editar Usuario**
```http
PUT /api/usuarios/{usuario_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "usuario": "usuario_actualizado",
  "correo": "nuevo@lahornilla.cl",
  "id_sucursalactiva": 103
}
```

### **4. Eliminar Usuario**
```http
DELETE /api/usuarios/{usuario_id}
Authorization: Bearer <token>
```

---

## 👷 **Endpoints de Trabajadores**

### **1. Listar Trabajadores**
```http
GET /api/trabajadores/
Authorization: Bearer <token>
```

### **2. Crear Trabajador**
```http
POST /api/trabajadores/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rut": 12345678,
  "codigo_verificador": "9",
  "nombre": "Juan",
  "apellido_paterno": "Pérez",
  "apellido_materno": "González",
  "id_contratista": 1,
  "id_porcentaje": 1,
  "id_estado": 1
}
```

### **3. Editar Trabajador**
```http
PUT /api/trabajadores/{trabajador_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "nombre": "Juan Carlos",
  "apellido_paterno": "Pérez",
  "id_contratista": 1
}
```

### **4. Eliminar Trabajador**
```http
DELETE /api/trabajadores/{trabajador_id}
Authorization: Bearer <token>
```

---

## 🏢 **Endpoints de Contratistas**

### **1. Listar Contratistas**
```http
GET /api/contratistas/
Authorization: Bearer <token>
```

### **2. Crear Contratista**
```http
POST /api/contratistas/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rut": 98765432,
  "codigo_verificador": "1",
  "nombre": "Empresa Contratista SPA",
  "id_estado": 1
}
```

### **3. Editar Contratista**
```http
PUT /api/contratistas/{contratista_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "nombre": "Nueva Empresa SPA",
  "id_estado": 1
}
```

### **4. Eliminar Contratista**
```http
DELETE /api/contratistas/{contratista_id}
Authorization: Bearer <token>
```

---

## 🤝 **Endpoints de Colaboradores**

### **1. Listar Colaboradores**
```http
GET /api/colaboradores/
Authorization: Bearer <token>
```

### **2. Crear Colaborador**
```http
POST /api/colaboradores/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rut": 11111111,
  "codigo_verificador": "1",
  "nombre": "María",
  "apellido_paterno": "González",
  "apellido_materno": "López",
  "id_sucursalcontrato": 103,
  "id_cargo": 1,
  "fecha_nacimiento": "1990-01-01",
  "fecha_incorporacion": "2020-01-01",
  "id_prevision": 1,
  "id_afp": 1,
  "id_estado": 1
}
```

### **3. Editar Colaborador**
```http
PUT /api/colaboradores/{colaborador_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "nombre": "María José",
  "id_cargo": 2
}
```

### **4. Eliminar Colaborador**
```http
DELETE /api/colaboradores/{colaborador_id}
Authorization: Bearer <token>
```

---

## 📋 **Endpoints de Permisos**

### **1. Listar Permisos**
```http
GET /api/permisos/
Authorization: Bearer <token>
```

### **2. Crear Permiso**
```http
POST /api/permisos/
Authorization: Bearer <token>
Content-Type: application/json

{
  "nombre": "Juan",
"apellido_paterno": "Pérez", 
"apellido_materno": "González",
  "fecha_inicio": "2025-07-22",
  "fecha_fin": "2025-07-23",
  "motivo": "Cita médica",
  "id_tipopermiso": 1
}
```

### **3. Eliminar Permiso**
```http
DELETE /api/permisos/{permiso_id}
Authorization: Bearer <token>
```

---

## 🏷️ **Endpoints de Tarjas**

### **1. Listar Tarjas**
```http
GET /api/tarjas/
Authorization: Bearer <token>
```

### **2. Crear Tarja**
```http
POST /api/tarjas/
Authorization: Bearer <token>
Content-Type: application/json

{
  "nombre": "Tarja Nueva",
  "descripcion": "Descripción de la tarja"
}
```

---

## 📊 **Endpoints de Rendimiento Propio**

### **1. Listar Rendimientos Propios**
```http
GET /api/rendimientopropio/
Authorization: Bearer <token>
```

### **2. Crear Rendimiento Propio**
```http
POST /api/rendimientopropio/
Authorization: Bearer <token>
Content-Type: application/json

{
  "id_actividad": "actividad_id",
  "cantidad": 15.5,
  "observaciones": "Rendimiento propio"
}
```

---

## 🔧 **Endpoints de CECOs Especializados**

### **CECOs Administrativos**
```http
GET /api/opciones/cecos/administrativos
POST /api/opciones/cecosadministrativos
DELETE /api/opciones/cecosadministrativos/{id}
```

### **CECOs de Inversión**
```http
GET /api/opciones/cecos/inversion
POST /api/opciones/cecosinversion
DELETE /api/opciones/cecosinversion/{id}
```

### **CECOs de Maquinaria**
```http
GET /api/opciones/cecos/maquinaria
POST /api/opciones/cecosmaquinaria
DELETE /api/opciones/cecosmaquinaria/{id}
```

### **CECOs Productivos**
```http
GET /api/opciones/cecos/productivos
POST /api/opciones/cecosproductivos
DELETE /api/opciones/cecosproductivos/{id}
```

### **CECOs de Riego**
```http
GET /api/opciones/cecos/riego
POST /api/opciones/cecosriego
DELETE /api/opciones/cecosriego/{id}
```

---

## 📋 **Códigos de Estado HTTP**

- **200:** OK - Operación exitosa
- **201:** Created - Recurso creado exitosamente
- **400:** Bad Request - Datos inválidos
- **401:** Unauthorized - Token inválido o faltante
- **403:** Forbidden - Sin permisos
- **404:** Not Found - Recurso no encontrado
- **500:** Internal Server Error - Error del servidor

---

## 🚀 **Despliegue**

### **Variables de Entorno Requeridas:**
```env
DATABASE_URL=mysql+pymysql://UserApp:password@/database?unix_socket=/cloudsql/instance
SECRET_KEY=Inicio01*
JWT_SECRET_KEY=Inicio01*
FLASK_ENV=production
FLASK_DEBUG=0
K_SERVICE=apilhtarja
```

### **Dockerfile:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y gcc
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "app:app"]
```

---

## 📞 **Soporte**

- **URL de Producción:** `https://apilhtarja-927498545444.us-central1.run.app`
- **Base de Datos:** Cloud SQL MySQL
- **Autenticación:** JWT Bearer Token
- **CORS:** Configurado para desarrollo local y producción

---

## ✅ **Estado Actual**

- ✅ **Login funcionando**
- ✅ **Conexión a Cloud SQL establecida**
- ✅ **Todos los endpoints registrados**
- ✅ **Autenticación JWT implementada**
- ✅ **CORS configurado**
- ✅ **Despliegue en Cloud Run exitoso** 