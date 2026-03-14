# COMP 401 - Live Financial Risk Dashboard

## Overview

This project ingests live stock prices and historical price data, computes 60-day annualized volatility, and evaluates real-time price movements against historical risk levels to determine whether price changes are normal market noise or statistically significant deviations.

## Data sources:

Finnhub API: real-time stock quotes

Yahoo Finance (yfinance): historical price data

## Features

Real-time stock price ingestion

Historical price retrieval

60-day rolling volatility calculation

Log return computation

Cache layer for API efficiency + staying within limits

## Setup

Install dependencies:

- pip install -r requirements.txt

Run the project by running main to start collecting live quotes, then running the graphing script to begin live plotting. Run both simultaneously.

- python main.py

- python live_volalitility.py
