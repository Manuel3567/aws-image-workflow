uv build

uv pip install --target build .\dist\image_resizer-0.1.0-py3-none-any.whl

cd build

zip -r ../image_resizer_code.zip *