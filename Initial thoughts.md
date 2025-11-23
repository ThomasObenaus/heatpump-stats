# 1st prompt

I have a heatpump system from Viessmann and wanted to monitor its performance over time.
The system has an API that provides some data like supplypower and data from the temperature sensors. Sadly I can't consume power consumption data of the heatpump over the API.
But I have a Shelly Pro3EM installed to monitor the power consumption of the heatpump.

Now I want to build a software that fetches the data from both the Viessmann API and the Shelly device and stores it in a time series database for analysis and visualization.
Which database would here be the best I don't know yet, so I'm open for suggestions.
The software should be a web application with a nice dashboard to visualize the data.
The software should run in the end in a Docker container on my home server.

For the backend-part I would like to use python but also here I'm open for suggestions.
For the frontend-part I would like to use a modern web framework like React or Vue.js, please provide your recommendations.
