#!/bin/bash

SERVER="127.0.0.1"
PORT="1053"


read -r -p "Enter the query data file path: " QUERY_FILE
read -r -p "Enter the test duration in seconds: " DURATION
read -r -p "Enter the maximum query rate: " QUERY_RATE

if [ -z "$QUERY_FILE" ] || [ -z "$DURATION" ] || [ -z "$QUERY_RATE" ]; then
    echo ""
    echo "Error: All fields must be entered. Exiting."
    exit 1
fi

echo ""
echo "--- Starting dnsperf Test ---"
echo "Server: $SERVER (Port: $PORT)"
echo "Query File: $QUERY_FILE"
echo "Duration (seconds): $DURATION"
echo "Query Rate (QPS): $QUERY_RATE"
echo "-----------------------------"
echo ""

dnsperf -s "$SERVER" -p "$PORT" -d "$QUERY_FILE" -l "$DURATION" -Q "$QUERY_RATE"

EXIT_CODE=$? 

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Test completed successfully."
else
    echo ""
    echo "Exited with an error (Exit Code: $EXIT_CODE)."
fi