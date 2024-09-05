**_THIS IS A MIRRORED VERSION OF AN INTERNAL PRODUCTION REPOSITORY LAST UPDATED 2023-07-28_**

# DOR Mapping PIN Request API
API to generate a new PIN for parcels within a user's SDE named version

Application Author: _James Midkiff_  
Visual Design and Workflows Documentation: _Donna Short_

## User directions
**See _Workflows for Pin Application.docx_ for the steps to take for the application's most common workflows.**

A user with access to the `dor_mapping` database should visit the login page _<production_site>_, input their login credentials, and then specify the _Addr_Std_ and _MapReg_ of the parcels they are looking to assign PINs to. The application will begin an edit session in the named version for the user, and search for parcels that: 
1. Match this _Addr_Std_ and _MapReg_ (case-sensitive and punctuation sensitive!)
1. Have a NULL PIN value, and 
1. Have a _status_ of 1 or 3

For all parcels found, the application will assign the next available PIN number > 1,999,000,000 into _parcel_rev_evw_ using that user's SDE named version. The application will then display these records and the new PINs to the user, who can then repeat the same action for a new _Addr_Std_ and _MapReg_ or logout of the application. PIN will increment for each successful record edited by a user in their named_version, so there is no possibility of receiving the same PIN. In other words, PIN is independent of users and will globally increment by each call regardless of who called for the increment. Leave either section blank to locate parcels with NULL or empty _Addr_Std_ and _MapReg_ values. 

Note that the spelling and case for _Addr_Std_ and _MapReg_ must be exact, including punctuation. Some addresses are listed as "XX AVE" while others are listed as "XX AVENUE" for instance, so if you are unable to locate a parcel that you believe is in the database, try different spelling variations. 

If multiple parcels share the same PIN and you would like them to all have a new PIN, set the PIN to NULL in ArcGIS Pro inside your named version and then use the application to assign them all a new PIN. 

All successful PIN requests will be logged into the table _dor_mapping.dor.pin_request_test_. 

Valid usernames will appear in the "ROLES" for `dor_mapping` and have an already existing SDE version. They are likely your AD username with "_" instead of "."

### PIN Conflicts
The application cannot easily guarantee that users will not assign conflicting PINs to parcels (either the same PIN to different parcels or different PINs to the same parcel). To avoid this, please: 
1. Avoid working on the same parcels as other users
1. Avoid manually creating PINs outside of the application 

If the application generates a PIN that is already in use, it will fail to process the request and instead return the pre-existing PINs and the number of existing active parcels using that PIN. This is something that must be manually addressed; contact CityGeo team members Alex Waldman, Donna Short, and James Midkiff at _<email_address>_.

SDE Versions reconcile every Sunday.

## Test-Version
There is a test version which if it is running will be accessible at the public IP address of the server on port 8080, likely _<test_site>_. It will also indicate that it is the testing version at the top of the webpage.

To run the test version of the application, there is an additional system daemon, whose service is at `/etc/systemd/system/flaskapp.service` which also contains the AWS environment variables for boto3. This can be started as normal with `sudo systemctl start flaskapp_testing.service` and checked with `sudo systemctl status flaskapp_testing.service`. The status of all flask related systemd services can be checked with `sudo systemctl list-unit-files --type service -all | grep "flask"`, and it can be followed with `sudo journalctl -fu flaskapp_testing.service`. 

**When not testing, this service should be explicitly stopped with `sudo systemctl stop flaskapp_testing.service`**

Note that the service will run 
```
/scripts/dor_mapping_pin_request_api/venv/bin/flask --app '/scripts/dor_mapping_pin_request_api/dor_mapping:create_app(testing=True, commit=True)' --debug run -h 0.0.0.0 -p 8080
```
which will load the _testing_ and _commit_ variables as True, use the E3 test database rather than the E3 prod database, allow the application to be accessible on port 8080 from anyone who can access our City network. This is only safe to run because the instance has security groups that restrict traffic to the VPN and City internet.

## Developers
This Flask module generally follows the [Flask Tutorial](https://flask.palletsprojects.com/en/2.2.x/tutorial/), in that it: 
* Uses a blueprint that is registered to an application factory
* Is layed out as an installable package
* Uses a `/static` for static CSS and image files

Beginning and ending named_version edit sessions can permanently hang if too many edit sessions have been started without a database connection `commit()` or `rollback()`.

If additional _parcel_type_ values should be added to the list of options, edit the file `dor_mapping/templates/auth/record.html`. 

### SDE
A named version edit session can only be set or started when logged in as the user that is the owner of that named version. This was tricky to determine, but was noted from looking at the source of the function `sde.sde_set_current_version()` in DBeaver. Therefore, the actual application will in order: 
1. "Login the user" i.e. create a database connection as the user (thereby confirming their username and password are correct to access the database)
2. "Login as version owner" i.e. create a db connection as DOR
3. Confirm that a named version edit session can be started as the user
4. If this all succeeds, then advance the user to the next route

The source of a named table version can be inspected by looking at its source in an application such as DBeaver. Use that source code and _sde.sde_table_registry_ to determine the source tables that a view is built off of. The "delta" tables are listed as _dor.a**int**_ and _dor.d**int**_ where _a_ stands for appends and _d_ stands for deletes as a means to track all appends, deletes, and changes (append and delete) and **int** is an integer referenced on _sde.sde_table_registry_. 

On their own, users will generally reconcile and post to _QAQC_ version which functions as a "test" version before the "prod" version called _DEFAULT_, and it functions similar to a git pull/push. 

When using a database adaptor such as `psycopg`, the queries to commit SQL must occur _after_ every single SDE statement to end the edit named version session, **_NOT_** before; otherwise the session won't be fully closed and users will be unable to reconcile and post their changes. 

### Server-side: 
The Flask applications uses a Gunicorn WSGI server and an nginx HTTP server. This process closely follows this [walk-through](http://howto.philippkeller.com/2022/05/02/How-to-deploy-flask-app-with-gunicorn-and-nginx-on-amazon-linux-2-ec2/).

To manually launch `gunicorn`, run `gunicorn 'dor_mapping:create_app()'`, but gunicorn is being launched by `systemd`. There is a file located at `/etc/systemd/system/flaskapp.service` which also contains the AWS environment variables for boto3. To follow the logs generated by gunicorn, run `sudo journalctl -fu flaskapp.service`. These logs should be automatically rotated and deleted from the defaults given in `/etc/systemd/journald.conf`, and the log files themselves are located at `/var/log/journal/<systemid>`, though they are not human-readable and are only designed to be read by `journalctl`. If you include `--access-logfile -` in the gunicorn command, you may get too much noise in the log files and stdout as a result of AWS Load Balancer health checks. 

`nginx` has a configuration file located at `/etc/nginx/conf.d/app.conf`, which is loaded by `/etc/nginx/nginx.conf`. 

Both of these will now be running in background daemons, so you are free to close the ssh session and go to the _public_ IP address given with `ip a` and `:80`. You can see the ports in use with `sudo lsof -i -P -n | grep LISTEN`

Only one application can use a port at the same time - you can use `sudo pkill <application>` or `sudo kill <process_id>`, but use that carefully! If making any changes, run `sudo systemctl restart nginx` for `nginx` or `gunicorn`. 

When not using `systemd`, the application can be launched with `sudo ./venv/bin/python -m flask --app dor_mapping/ run -h 0.0.0.0 -p 80 --debugger`, or if looking to just run locally, use `flask --app dor_mapping/ --debug run`.

### Server-Less Components
There is a load-balancer `dor-pin` with HTTP/HTTPS listeners. The HTTPS listener uses the SSL certificate .citygeo.phila.city and will forward traffic to the `dor-pin` target group which currently includes the `citygeo-linux-webserver` ec2-instance. The load balancer will perform a health check every 20 seconds on the `/` route.

Future applications would be in Docker Containers and deployed to AWS ECS via Terraform for more serverless and load-balancing approach. 

### Files
* `/`  
    * `README.md` - This document
    * `pyproject.toml` - TOML file to register this repository as a package
    * `.gitignore` - Gitignore file
    * `dor_mapping/` 
        * `templates/` - HTML files
            * `auth/` - Child templates utilized by Flask Blueprint
                * `login.html` - `/login` endpoint for logging in
                * `record.html` - `/record` endpoint for inputting information to record
                * `result.html` - `/result` endpoint for displaying the table of updated information
            * `layout.html` - A parent template that is extended by all child templates
        * `bp.py` - The front-end file that contains the blueprint (named "auth") that provides the routes offered by the Flask application
        * `db.py` - File that controls database actions and interactions, called by `bp.py`
        * `__init__.py` - File that contains the Flask application factory and that registers the repostory as an installable package
        * `postgres_code.py` - Miscellaneous postgresql commands
        * `postgres_sde.py` - Postgresql commands for SDE operations
    * `/static`
        * `favicon.ico` - The "favicon" used to give an image to the application tab in the browser
        * `styles.css` - The overriding CSS file used for styling. Created by Donna Short.

### Tables
| Database | Schema | Name | Type | Usage |
| - | - | - | - | - |
| dor_mapping | dor | | roles | The roles that someone can log into the database with | 
| dor_mapping | sde | sde_versions | table | List of current SDE named versions | 
| dor_mapping | dor | pin_request | table | PIN request logging table (will need to grant privileges to all editors for this table) | 
| dor_mapping | dor | parcel_rev_evw | view | Where to check if record exists (in correct named version) | 
| dor_mapping | sde | sde_table_registry | table | Lists the registration_id and the corresponding table for a particular view | 
| dor_mapping | dor | pancel_evw | view | DO NOT USE - Out of date, based on parcel_old | 
