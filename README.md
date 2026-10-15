# FAiND

**AI-assisted lost-and-found platform for university campuses.**

FAiND is designed to make recovering lost items on campus more organised, traceable and safer. Instead of relying on scattered WhatsApp messages or students arranging direct handovers with strangers, FAiND connects lost-and-found reports with official campus drop points where items can be received and verified by authorised staff.

The initial deployment is designed for **Ghana Communication Technology University (GCTU)**.

## The problem

Campus lost-and-found processes are often fragmented. A student might report a lost item in one group, while someone who found it posts somewhere completely different. Even when the two people find each other, there is still the question of how to safely verify ownership and return the item.

FAiND tries to bring the whole process into one system.

## How it works

1. A student reports a lost item.
2. A finder can report a found item without creating an account.
3. FAiND uses the item's information to identify potential matches.
4. Found items are directed to an official campus drop point.
5. A campus authority confirms the item has been received.
6. A potential owner submits a claim with additional information about the item.
7. The authority reviews the claim and verifies the owner in person.
8. The handover is recorded and the item is marked as returned.

The AI is used to assist with **matching and discovery**, while the final ownership decision remains with a human authority.

## Key features

* Lost and found item reporting
* AI-assisted item matching
* Anonymous found-item reporting
* Official campus drop points
* Authority and administrator dashboards
* Claim and verification workflow
* QR-based drop-off confirmation
* Item status tracking
* Notifications
* Token rewards for finders
* Image uploads
* Role-based access
* Two-factor authentication for authority accounts
* PWA support

## Tech stack

### Frontend

* React
* Vite
* React Router
* TanStack React Query
* Tailwind CSS
* Axios
* Vite PWA

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* JWT authentication
* PyOTP
* APScheduler

### AI / matching

* Sentence Transformers
* scikit-learn
* ImageHash
* NumPy

### Other

* Cloudinary
* QR code generation
* Web Push notifications

## Project structure

```text
FAiND/
├── frontend/    # React/Vite application
├── backend/     # FastAPI API and business logic
└── docs/        # Architecture and development documentation
```

## Project status

FAiND is an actively developed project. The current version focuses on an institutional drop-point model for handling found items and ownership verification.

## My role

I am responsible for the development of the project across the frontend and backend, including the application architecture, API development, database integration, authentication, matching logic, and product workflows.

## Why I built it

I wanted to solve a problem that students actually experience rather than build another project that only demonstrates a technology. Building FAiND has also given me experience dealing with the parts of software development that are less obvious from a classroom assignment - changing requirements, database design, authentication, debugging, edge cases and deciding how technology should fit into the actual user experience.
