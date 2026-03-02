##FOR TEAMMATES



#IN APP FILE RUN COMMAND
    cp .env.example .env

#TO RUN LOCALLY

    python -m venv venv
    venv\Scripts\activate           -Creates venv

    pip install -r requirements.txt -INSTALLS Required libraries
    python run.py                   -Runs backend locally



#TO RUN ON DOCKER


    #ON FIRST BUILD:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up --build


    #AFTER FIRST BUILD:
        #RUN FOREGROUD:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up
        #RUN BACKGROUND:
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up -d
        
        #STOP
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml down 


    #Rebuild
        docker compose -f docker-compose.yml -f docker-compose.frontend.yml up --build --force-recreate





