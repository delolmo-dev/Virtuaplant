#!/bin/sh

echo "VirtuaPlant -- Bottle-filling Factory"
echo "- Starting World View"
python3 world.py &
echo "- Starting HMI"
python3 hmi.py &