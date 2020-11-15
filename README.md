# CRVX
_**C**limbing **R**ecord **V**isualisation e**X**perience_

CRVX (pronounced __crux__) is an app to help visualise climbing training data.
The app uses Google Sheets as a database to store the training data, [Streamlit](https://www.streamlit.io/) + 
[Pandas](https://pandas.pydata.org/) + [Altair](https://altair-viz.github.io/) 
to analyse and visualise the data. It's deployed on [Heroku](https://www.heroku.com/).

http://crvx.herokuapp.com/

## Deployment instructions

1. Make a copy of the Google Sheets [Climbing Data Template](https://docs.google.com/spreadsheets/d/1GnTS8l9lzXaWAHClnkKmIEp6vs_75FJZ1cPcgaeWxVA/edit?usp=sharing). 
Rename it to "Climbing Data", which is the spreadsheet CRVX will look for when querying the Google API.
1. Fill in your training data. Notice the named range "raw_data", this is where CRVX app will pull data from. Note that 
everything else outside the named range (i.e. the computed data) is not queried and is simply for the user's benefit when
looking at the data spreadsheet.
1. Create a [service account key](https://cloud.google.com/iam/docs/creating-managing-service-account-keys#iam-service-account-keys-create-console) so CRVX app can access your training logbook.
1. Create a heroku project, add [this 3rd party Google Credentials build pack](https://elements.heroku.com/buildpacks/buyersight/heroku-google-application-credentials-buildpack), 
and follow the instructions on that page to add your service account key to your project's config vars.
1. Deploy your project on Heroku! The [GitHub Integration](https://devcenter.heroku.com/articles/github-integration) makes it easy. 
The free tier should be sufficient unless you have other apps already deployed.
