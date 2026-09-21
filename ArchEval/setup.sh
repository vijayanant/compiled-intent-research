#!/bin/bash
set -e

# Always run from the ArchEval directory
cd "$(dirname "$0")"

echo "================================================="
echo "  Setting up ArchEval Environment"
echo "================================================="

# 1. Ensure required directories exist
mkdir -p logs config

# 2. Ensure config/akshara_config.toml exists
if [ ! -f "config/akshara_config.toml" ]; then
    echo "Creating default config/akshara_config.toml..."
    cat << 'EOF' > config/akshara_config.toml
llama_endpoint = "http://localhost:11434/v1/embeddings"
embedding_model = "nomic-embed-text:latest"
embedding_dimensions = 768
intent_dir = ".intent_akshara_db"
lancedb_path = ".intent_akshara_db/lancedb"
EOF
fi

# 3. Setup Python Virtual Environment
if command -v uv &> /dev/null; then
    echo "Using uv for fast virtual environment setup..."
    if [ ! -d ".venv" ]; then
        uv venv .venv
    fi
    source .venv/bin/activate
    echo "Installing dependencies via uv..."
    uv pip install -r requirements.txt
else
    echo "Using standard Python venv & pip..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    echo "Installing dependencies via pip..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 4. Check intent CLI & pre-index LanceDB if Ollama is running
echo "Checking intent CLI and vector database..."
if command -v intent &> /dev/null; then
    if [ ! -d ".intent_akshara_db" ]; then
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "Pre-indexing Akshara specifications into LanceDB (.intent_akshara_db)..."
            intent --config config/akshara_config.toml index datasets/akshara_specs
            echo "Vector database initialized successfully."
        else
            echo "Note: Ollama is not currently running. Pre-indexing deferred."
            echo "Start Ollama and run ./scripts/run_benchmarks.sh before running RAG evaluations."
        fi
    else
        echo "Vector database .intent_akshara_db is ready."
    fi
else
    echo "Note: 'intent' binary not found on PATH."
    echo "Install via: cargo install --git https://github.com/vijayanant/compiled-intent.git"
    echo "Or download prebuilt binary from: https://github.com/vijayanant/compiled-intent/releases"
fi

echo "================================================="
echo "Setup complete! You can now run the benchmarks."
echo "================================================="

