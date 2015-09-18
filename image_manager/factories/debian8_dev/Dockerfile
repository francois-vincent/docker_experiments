FROM debian:8

RUN apt-get update && apt-get install -y python-pip git postgresql-server-dev-all python-dev libzmq-dev debhelper
RUN apt-get install -y build-essential cmake gcc g++ libboost-all-dev liblog4cplus-1.0-4 liblog4cplus-dev libgoogle-perftools4 libgoogle-perftools-dev
RUN apt-get install -y libprotobuf9 libprotobuf-dev libprotoc9 protobuf-compiler libproj0 libproj-dev libosmpbf-dev libpqxx-dev

RUN pip install pip virtualenv

# add user and group jenkins, with specific userid and groupid, never fail
RUN groupadd -g {groupid} jenkins; exit 0
RUN useradd -u {userid} -g {groupid} jenkins && echo "jenkins:jenkins" | chpasswd; exit 0

CMD ["/bin/bash"]
