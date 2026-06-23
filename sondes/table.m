clear all

path = 'D:\Table\Sondes\';

files = dir([path, 'so*']);
l = length(files);
filename = cell(l, 1);
filename_full = cell(l, 1);
for k = 1:l
    filename{k} = files(k).name;
    filename_full{k} = [path, filename{k}];
end

[launch_time, serial_number, flow_rate, bg_current] = ...
    SondeInfo(filename_full);

date_str = cellstr(datestr(launch_time,31));

headr = {...
    'Filename', ...
    'Launch time', ...
    'Serial number', ...
    'Flow rate', ...
    'Background current'};

xlswrite('table', headr, 1, 'A1');
xlswrite('table', filename, 1, 'A2');
xlswrite('table', date_str, 1, 'B2');
xlswrite('table', serial_number', 1, 'C2');
xlswrite('table', flow_rate', 1, 'D2');
xlswrite('table', bg_current', 1, 'E2');

