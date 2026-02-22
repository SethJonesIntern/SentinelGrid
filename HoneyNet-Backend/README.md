##FOR TEAMMATES

#TO RUN LOCALLY
    pip install -r requirements.txt -INSTALLS Required libraries
    python run.py                   -Runs backend locally



#TO RUN ON DOCKER


    #ON FIRST BUILD:
        docker compose up --build


    #AFTER FIRST BUILD:
        #RUN FOREGROUD:
        docker compose up
        #RUN BACKGROUND:
        docker compose up -d
        
        #STOP
        docker compose down 


    #Rebuild
        docker compose up --build --force-recreate





