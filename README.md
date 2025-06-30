# ADVANCED RECOMMENDATION SYSTEM FOR E-COMMERCE APPS
*This was a Bsc dissertation project.*

#### Introduction

The backend is built using FastAPI, a high-performance web framework for Python. It is
responsible for handling all business logic, authentication, recommendation generation,
and database interactions. The backend server is developed using a modular monolithic
architecture, where all core functionalities, including API routing, authentication,
recommendation logic, and database access, are contained within a single unified
codebase but loosely coupled. This approach simplifies development and deployment in
the early stages of the project, offering ease of integration and centralized control.
As the system grows, this monolithic structure provides a solid foundation that can later be
modularized or refactored into microservices if scalability and separation of concerns
become priorities.
- **API Layer**: Exposes endpoints for interacting with the system, including endpoints
for user authentication, recommendations, and data management.
- **Business Logic Layer**: Contains the recommendation algorithms, including
collaborative filtering using scikit-surprise (KNN) and content-based filtering using
scikit-learn (TF-IDF). Logic for interaction with products, cart manipulation, order
checkout and product rating are also included here.
- **Data Layer**: MongoDB is used to store all persistent data, including user profiles,
ratings, product data, and recommendations. FastAPI interacts with the database
using Motor for asynchronous database queries.
- **Authentication Layer**: Uses JWT (JSON Web Tokens) for secure user authentication.
The tokens are passed in API requests to authenticate and authorize user actions.

#### Dependencies

- Python Version: >= `3.10` <= `3.12` (`scikit-surprise` at the moment does not work well with Python version `3.13`)
- fastapi==0.115.12
- Jinja2==3.1.6
- motor==3.7.0 and pymongo==4.11.3
- pydantic==2.11.2
- pydantic-settings==2.8.1
- pydantic_core==2.33.1
- PyJWT==2.10.1
- bcrypt==4.3.0
- emails==0.6
- *And others listed in the `requirements.txt` file*

#### Modular Monolith Architecture
![system-architecture drawio](https://github.com/user-attachments/assets/f365b98f-0169-4044-9d41-50b0565a5c93)

#### NoSQL Data Model Diagram
![mongodb-erd drawio](https://github.com/user-attachments/assets/1ae98615-1c04-479b-8fe3-1159795dce4c)

#### Running locally (macOS)?
- `docker-compose up -d` to start docker services in the background detached from the terminal.
- create a virtual environment: `python3 -m venv <virtual environment name>`
- enter your virtual environment: `source <virtual environment name>/bin/activate`
- install packages listed in the requirements.txt file: `pip install -r requirements.txt`
- start server: `uvicorn app.main:application --host 0.0.0.0 --port 8000`, for reloads on code change the `--reload` flag can be added.

The server will now be running on port `8000`.
