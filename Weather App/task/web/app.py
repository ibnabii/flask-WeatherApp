import requests
import sys

from datetime import datetime, timedelta
from http import HTTPStatus
from json import loads

from flask import Flask, render_template, request, redirect,  flash, get_flashed_messages
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, create_engine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supposedlyItsNeededForFlashMsgs'
Base = declarative_base()


def db_engine():
    return create_engine(r'sqlite:///weather.db', echo=True)


def db_session():
    Session = sessionmaker(bind=db_engine())
    return Session()


class City(Base):
    __tablename__ = 'cities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)


def time_of_day(sunrise, sunset, time):
    rise = datetime.fromtimestamp(sunrise)
    sset = datetime.fromtimestamp(sunset)
    now = datetime.fromtimestamp(time)
    hours_span = timedelta(hours=2)
    if rise - hours_span < now < rise + hours_span or sset - hours_span < now < sset + hours_span:
        return 'evening-morning'
    if rise < now < sset:
        return 'day'
    return 'night'


def get_weather(city, identifier=None):
    url = 'https://api.openweathermap.org/data/2.5/weather?q=' + city + \
          '&appid=897f769210c666f37b2ce5d5456f43e4&units=metric'
    r = requests.get(url)
    if r:
        resp = loads(r.text)
        return {'city': city.upper(),
                'time': time_of_day(resp['sys']['sunrise'], resp['sys']['sunset'], resp['dt']),
                'state': resp['weather'][0]['main'],
                'degree': round(resp['main']['temp'],),
                'id': identifier}
    else:
        return None


@app.route('/')
def main():
    session = db_session()
    weather_list = [get_weather(x, y) for x, y in session.query(City.name, City.id) if get_weather(x, y)]
    session.close()
    return render_template('index.html', weather=weather_list)


@app.route('/add', methods=['POST'])
def add_city():
    session = db_session()
    if get_weather(request.form['city_name']):
        try:
            session.add(City(name=request.form['city_name'].upper()))
            session.commit()
        except IntegrityError:
            flash('The city has already been added to the list!')
        session.close()
    else:
        flash("The city doesn't exist!")
    return redirect('/', HTTPStatus.SEE_OTHER)


@app.route('/delete/<identifier>', methods=['POST'])
def delete_city(identifier):
    print(identifier)
    session = db_session()
    session.query(City).filter(City.id == identifier).delete()
    session.commit()
    session.close()
    return redirect('/', HTTPStatus.SEE_OTHER)


# don't change the following way to run flask:
if __name__ == '__main__':
    # establish database
    Base.metadata.create_all(db_engine())
    _debug = True
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port, debug=_debug)
    else:
        app.run(debug=_debug)
