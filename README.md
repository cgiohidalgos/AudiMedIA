# AudiMedIA

Sistema de auditoría médica concurrente con inteligencia artificial para instituciones hospitalarias colombianas.

## Estructura del proyecto

```
AudiMedIA/
├── frontend/          # React + Vite + Tailwind + shadcn/ui
├── backend/           # Python FastAPI + SQLite
├── docker-compose.yml # Orquestación local completa
└── README.md
```

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) |
| Base de datos | SQLite (aiosqlite) |
| IA | OpenAI GPT-4o (extracción + chat) |
| PDF | PyMuPDF + Tesseract OCR |
| Auth | JWT + RBAC (admin / auditor / coordinador) |
| Infra | Docker + docker-compose |

## Inicio rápido

### 1. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
# Editar backend/.env y agregar OPENAI_API_KEY
```

### 2. Levantar con Docker

```bash
docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/v1
- Documentación API: http://localhost:8000/api/docs

### 3. Desarrollo local (sin Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Arquitectura del backend

```
backend/
├── app/
│   ├── main.py                    # Entry point FastAPI
│   ├── core/
│   │   ├── config.py              # Settings con pydantic-settings
│   │   └── security.py            # JWT + bcrypt
│   ├── db/
│   │   └── session.py             # AsyncSession + Base ORM
│   ├── models/
│   │   ├── user.py                # Usuario + roles RBAC
│   │   ├── patient.py             # Historia clínica / caso
│   │   └── audit.py               # Sesión, hallazgos, chat
│   ├── schemas/                   # Pydantic I/O schemas
│   ├── api/v1/
│   │   ├── deps.py                # Auth dependencies
│   │   ├── router.py              # Router principal
│   │   └── endpoints/
│   │       ├── auth.py            # Login / registro
│   │       ├── users.py           # Gestión usuarios (admin)
│   │       ├── upload.py          # Carga de PDFs
│   │       ├── patients.py        # Historias + hallazgos
│   │       ├── chat.py            # Chat con historia
│   │       └── dashboard.py       # Métricas financieras
│   ├── services/
│   │   ├── ai/
│   │   │   ├── extractor.py       # Extracción variables (LLM)
│   │   │   ├── audit_modules.py   # 4 módulos de auditoría
│   │   │   └── chat_service.py    # Chat RAG con historia
│   │   └── document/
│   │       ├── pdf_extractor.py   # PyMuPDF + Tesseract OCR
│   │       └── anonymizer.py      # Anonimización PII
│   └── workers/
│       └── pdf_worker.py          # Pipeline completo de procesamiento
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario |
| POST | `/api/v1/auth/login` | Iniciar sesión |
| GET | `/api/v1/users/me` | Perfil del usuario actual |
| POST | `/api/v1/upload/` | Cargar PDFs (máx. 5) |
| GET | `/api/v1/upload/status/{id}` | Estado del procesamiento |
| GET | `/api/v1/patients/` | Listar pacientes auditados |
| GET | `/api/v1/patients/{id}` | Detalle del paciente |
| GET | `/api/v1/patients/{id}/findings` | Hallazgos de auditoría |
| PATCH | `/api/v1/patients/{id}/findings/{fid}` | Marcar hallazgo resuelto |
| POST | `/api/v1/chat/` | Chat con historia clínica |
| GET | `/api/v1/chat/history/{patient_id}` | Historial del chat |
| GET | `/api/v1/dashboard/metrics` | Métricas financieras |

## Roles del sistema

| Rol | Descripción |
|-----|-------------|
| `admin` | Gestión de usuarios, configuración del sistema |
| `auditor` | Carga PDFs, analiza historias, usa el chat |
| `coordinador` | Dashboard financiero, reportes ejecutivos |
| `equipo_medico` | Ver pendientes de sus pacientes |

## Usuarios por defecto

Al ejecutar `docker compose up` se crean automáticamente los siguientes usuarios (si no existen):

| Rol | Email | Password |
|-----|-------|----------|
| `superadmin` | superadmin@audiomedia.co | Superadmin1234 |
| `admin` | admin@audiomedia.co | Admin1234 |
| `auditor` | auditor@audiomedia.co | Auditor1234 |
| `coordinador` | coordinador@audiomedia.co | Coordinador1234 |
| `equipo_medico` | medico@audiomedia.co | Medico1234 |

## Normativa aplicada

- Ley 1438 de 2011
- Decreto 780 de 2016
- Resolución 1995 de 1999 (historia clínica)
- CIE-10 / CUPS
- Guías clínicas MinSalud Colombia
