#!/bin/bash
# Render build script

echo "Installing NLTK data..."
python3 - << 'EOF'
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
EOF

echo "Build completed!"
