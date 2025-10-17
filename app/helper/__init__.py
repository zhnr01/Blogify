import pendulum
import humanize

def format_relative_time(dt):
    pendulum_dt = pendulum.instance(dt, tz=pendulum.local_timezone())
    time_difference = pendulum.now() - pendulum_dt
    print(pendulum.now(), pendulum_dt)
    relative_time = humanize.naturaldelta(time_difference)

    return relative_time
