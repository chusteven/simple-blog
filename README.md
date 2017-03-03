# simple-blog
A simple weblog with search functionality based on a [tutorial](http://charlesleifer.com/blog/how-to-make-a-flask-blog-in-one-hour-or-less/) found at Charles Leifer's blog.

# Setting up your virtual environment

Install pip, python-dev, and python-virtualenv packages. On Mac OS, this looks as follows:

````
brew install python-pip python-dev python-virtualenv
````

Set up a Python virtual envrionment and activate it:

````
virtualenv flask-blog
source flask-blog/bin/activate
````

Note: to deactivate this virtaul environment, simply run:

````
deactivate
````

# Install requirements

Install the requirements for this particular project:

````
pip install -r requirements.txt
````

# Running the application

Run the application as follows:

````
python app.py
````
