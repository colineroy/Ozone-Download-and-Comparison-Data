function [da,nname,chname,nvalues,chvalues]=parluku2(faili)

fid=fopen(faili);
for i=1:6
    fgetl(fid);
end
da=fscanf(fid,'%d',3);
da=da';
for i=1:5
    fgetl(fid);
end
rivi=fgetl(fid);
ncol=sscanf(rivi,'%d');
c=fscanf(fid,'%f',ncol);
mis=fscanf(fid,'%f',ncol);
fgetl(fid);
for i=1:ncol
    columns{i}=fgetl(fid);
end
ntot=fscanf(fid,'%d',1);
nch=fscanf(fid,'%d',1);
nnum=ntot-nch;
caux=fscanf(fid,'%f',nnum);
missaux=fscanf(fid,'%f',nnum);
chlen=fscanf(fid,'%d',nch);
fgetl(fid);
for i=1:nch
    fgetl(fid);
end
for i=1:nnum
    nname{i}=fgetl(fid);
end
for i=1:nch
    chname{i}=fgetl(fid);
end
ncom1=fscanf(fid,'%d',1);
fgetl(fid);
if ncom1>=1
    for i=1:ncom1
        com1{i}=fgetl(fid);
    end
end
ncom2=fscanf(fid,'%d',1);
fgetl(fid);
if ncom2>=1
    for i=1:ncom2
        com2{i}=fgetl(fid);
    end
end
idp1=fgetl(fid);
nvalues=fscanf(fid,'%f',nnum);
fgetl(fid);
for i=1:nch
    chvalues{i}=fgetl(fid);
end
fclose(fid);
