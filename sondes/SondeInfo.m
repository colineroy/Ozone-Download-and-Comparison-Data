function [launch_time,serial_number,flow_rate,bg_current]=SondeInfo(file_name)

le=length(file_name);

launch_time=NaN(1,le);
serial_number=cell(1,le);
flow_rate=NaN(1,le);
bg_current=NaN(1,le);
for k=1:le
    [da,nname,chname,nvalues,chvalues]=parluku2(file_name{k});
    nname=lower(strtrim(nname));
    chname=lower(strtrim(chname));
    chvalues=strtrim(chvalues);
    
    ix=strmatch('launch time',nname);
    if ~isempty(ix)
        launch_time(k)=datenum(da)+nvalues(ix(1))/24;
    end
    ix=strmatch('serial number of ecc',chname);
    if ~isempty(ix)
        serial_number{k}=chvalues{ix(1)};
    end
    ix=strmatch('sensor air flow rate (ozonesonde pump only operating)',nname);
    if ~isempty(ix)
        flow_rate(k)=nvalues(ix(1));
    end
    ix=strmatch('background sensor current in the end of the pre-flight calibration',nname);
    if ~isempty(ix)
        bg_current(k)=nvalues(ix(1));
    end
end  