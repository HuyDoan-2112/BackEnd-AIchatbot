# Backend API Test Suite

This folder contains comprehensive HTTP test files for all backend API endpoints using VS Code REST Client extension.

## 📁 Test Structure

```
tests/endpoint/
├── auth/
│   ├── login.http          # Authentication (Login, Signup, Logout)
│   └── user.http           # User profile management
├── company/
│   └── company.http        # Company CRUD + Member management
├── project/
│   ├── project.http        # Project CRUD
│   └── projects.http       # Advanced project features
├── chat/
│   └── chat.http           # Chat completions, history, streaming
├── document/
│   └── documents.http      # Document upload and management
├── embedding/
│   └── embeddings.http     # Vector embeddings & search
├── model/
│   └── models.http         # Model listing and comparison
├── retrieval/
│   └── retrieval.http      # Document retrieval (RAG)
└── README.md               # This file
```

## 🚀 Getting Started

### Prerequisites

1. **VS Code Extension**: Install [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. **Running Backend**: Ensure the server is running on `http://localhost:8000`
3. **Environment Setup**: Backend should have PostgreSQL and Redis configured

### How to Use

1. **Open any .http file** in VS Code
2. **Click "Send Request"** (or use `Ctrl+Alt+R`) on any request
3. **View response** in the sidebar
4. **Reference previous responses** using `{{variableName.response.body.$.path}}`

## 📋 Test Files Overview

### 1. **Authentication** (`auth/`)

#### `login.http`
- ✅ User signup
- ✅ User login with email/password
- ✅ Token refresh
- ✅ Logout

#### `user.http`
- ✅ Get current user profile
- ✅ Update user profile
- ✅ Refresh access token

**Example Flow:**
```
Signup → Login → Use access_token for other APIs
```

---

### 2. **Company Management** (`company/company.http`)

Demonstrates complete company lifecycle:

- ✅ **Create Company** - Create new company
- ✅ **Read** - Get company details, list companies
- ✅ **Update** - Modify company information
- ✅ **Delete** - Remove company
- ✅ **Member Management** - Add/remove members, list members

**Example Flow:**
```
User 1 Signup
  ↓
Create Company (Company Owner)
  ↓
User 2 Signup
  ↓
Add User 2 as Member
  ↓
List Members
  ↓
Remove User 2
  ↓
Delete Company
```

---

### 3. **Project Management** (`project/projects.http`)

Project CRUD operations:

- ✅ **Create Project** - Create in a company
- ✅ **Get Project** - Retrieve project details
- ✅ **List Projects** - Get all projects
- ✅ **Update Project** - Modify project info
- ✅ **Get Conversations** - List chats in project
- ✅ **Delete Project** - Remove project

**Dependencies:**
- Requires existing company (create first)

---

### 4. **Chat & Conversations** (`chat/chat.http`)

Full chat lifecycle testing:

- ✅ **Anonymous Chat** - Chat without authentication (not persisted)
- ✅ **Authenticated Chat** - Chat with user (saved to DB)
- ✅ **Chat with History** - Multi-turn conversations
- ✅ **Streaming Chat** - Real-time responses (SSE)
- ✅ **Chat History** - Get conversation list and messages
- ✅ **RAG Chat** - Chat with document context

**Key Features:**
- Messages automatically saved for authenticated users
- Each chat creates/uses a conversation
- Supports multi-turn conversations
- Stream responses with `"stream": true`

**Example Flow:**
```
Signup & Create Company/Project
  ↓
Send Simple Chat
  ↓
Send Chat with company_id/project_id (saves to DB)
  ↓
Get Chat History
  ↓
List Messages
```

---

### 5. **Document Upload & Management** (`document/documents.http`)

Document handling:

- ✅ **Upload Document** - Create document record
- ✅ **Get Document** - Retrieve document details
- ✅ **List Documents** - By project or company
- ✅ **Update Document** - Modify metadata
- ✅ **Delete Document** - Remove document

**Features:**
- Tag documents for organization
- Associate with projects and companies
- Track file metadata (size, type, etc.)

---

### 6. **Embeddings & Vector Search** (`embedding/embeddings.http`)

Vector embedding operations:

- ✅ **Create Single Embedding** - Generate vector for text
- ✅ **Batch Embeddings** - Multiple texts at once
- ✅ **Search Embeddings** - Vector similarity search
- ✅ **Model Selection** - Choose embedding model

**Use Cases:**
- Semantic search
- Finding similar documents
- Preparing documents for RAG

---

### 7. **Models** (`model/models.http`)

Model information and selection:

- ✅ **List All Models** - See available models
- ✅ **List Chat Models** - Only chat models
- ✅ **List Embedding Models** - Only embedding models
- ✅ **Get Model Details** - Specific model info
- ✅ **Model Comparison** - Test different models on same query

**Available Models:**
- Chat: `openai/gpt-oss-20b`, `qwen/qwen3-4b`, etc.
- Embeddings: `text-embedding-embeddinggemma-300m`, etc.

---

### 8. **Document Retrieval (RAG)** (`retrieval/retrieval.http`)

Retrieval-Augmented Generation:

- ✅ **Upload Documents** - Create document corpus
- ✅ **Search Documents** - Query with vector similarity
- ✅ **Filtered Search** - Search with tags/filters
- ✅ **RAG Chat** - Answer questions using documents
- ✅ **Document Management** - CRUD operations

**Workflow:**
```
Create Company/Project
  ↓
Upload Documents
  ↓
Search Documents
  ↓
Chat with Document Context (RAG)
```

---

## 💡 Usage Patterns

### Pattern 1: Response Chaining

Use output from one request as input for next:

```http
### Create Company (saves ID in variable)
# @name create_company
POST {{base}}/companies
...
{ "name": "My Company" }

### Use Company ID in next request
POST {{base}}/projects
...
{ "company_id": "{{create_company.response.body.$.data.id}}" }
```

### Pattern 2: Authentication

All authenticated endpoints need Authorization header:

```http
Authorization: Bearer {{signup.response.body.$.data.access_token}}
```

### Pattern 3: Metadata for Persistence

To save chats to database, include metadata:

```json
{
  "model": "openai/gpt-oss-20b",
  "messages": [...],
  "metadata": {
    "company_id": "{{company_id}}",
    "project_id": "{{project_id}}",
    "conversation_title": "My Chat"
  }
}
```

### Pattern 4: Streaming

Enable streaming by setting `"stream": true`:

```json
{
  "model": "openai/gpt-oss-20b",
  "messages": [...],
  "stream": true
}
```

---

## 📊 Complete Workflow Example

Here's a full end-to-end workflow:

1. **Auth**: `auth/login.http` → Signup, Login
2. **Company**: `company/company.http` → Create company, add member
3. **Project**: `project/projects.http` → Create project
4. **Documents**: `document/documents.http` → Upload document
5. **Retrieval**: `retrieval/retrieval.http` → Search documents
6. **Chat**: `chat/chat.http` → Chat with document context (RAG)
7. **History**: `chat/chat.http` → Get conversation history

---

## 🔧 Configuration

### Base URL

All files use this variable:
```
@base = http://localhost:8000/api/v1
```

To change, edit the first line in any .http file:
```
@base = http://your-domain:port/api/v1
```

### Bearer Tokens

Replace `{{access_token}}` with real token from signup/login response.

---

## 🐛 Troubleshooting

### Problem: 401 Unauthorized
- **Solution**: Ensure `Authorization` header includes valid token from signup/login

### Problem: 404 Not Found
- **Solution**: Verify company/project/document IDs exist before using them

### Problem: 400 Bad Request
- **Solution**: Check JSON format, required fields, and field constraints

### Problem: 500 Internal Server Error
- **Solution**: Check server logs. May indicate database or service issue.

---

## 📝 Notes

- ⏱️ **Timestamps**: `{{$timestamp}}` generates unique values for usernames/emails
- 🔗 **Variables**: Use `@variable = value` to define custom variables
- 💾 **Cleanup**: Optional delete requests are included at the end of each file
- 🔐 **Security**: Never commit real API keys or tokens to version control

---

## 🎯 Next Steps

1. Start with `auth/login.http` to understand authentication
2. Follow `company/company.http` for basic CRUD operations
3. Explore `chat/chat.http` for conversation features
4. Try `retrieval/retrieval.http` for advanced RAG workflows

---

**Happy Testing! 🚀**

For more information, see the [REST Client Documentation](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
