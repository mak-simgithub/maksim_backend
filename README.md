# maksim_backend

Backend for my homepage, mainly to controll my little leech farm.

To run project, clone repo and set up virtaulenv with:

    `python3 -m venv virtualenv`
    `source virtualenv/bin/activate`
    `pip3 install -r requirements.txt`

then:

    `python3 -m uvicorn backend:app --reload --host 0.0.0.0`