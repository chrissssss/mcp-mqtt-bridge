# Contribution Guidelines

## Commit Messages

To maintain a clear and descriptive version history, please follow these guidelines for commit messages.

### Format

Each commit message consists of a **header** and a **body**.

```
<type>: <subject>
<BLANK LINE>
<body>
```

### Header

The header is a single line that contains a succinct description of the change.

-   **type**: This describes the kind of change that this commit is providing.
    -   `feat`: A new feature
    -   `fix`: A bug fix
    -   `docs`: Documentation only changes
    -   `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
    -   `refactor`: A code change that neither fixes a bug nor adds a feature
    -   `test`: Adding missing tests or correcting existing tests
    -   `chore`: Changes to the build process or auxiliary tools
-   **subject**: The subject contains a short description of the change.

### Body

The body should include the motivation for the change and contrast this with previous behavior. It should explain *why* you are making the change, providing the full context that led to it.

**Example:**

> feat: Initial MQTT ping-pong setup with Docker
> 
> This commit introduces a complete Docker Compose environment for a simple MQTT publisher/subscriber application.
> 
> The setup was created to fulfill the request for a containerized Python application demonstrating MQTT communication.
