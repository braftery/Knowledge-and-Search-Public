"""Run the API locally: python -m api"""

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
