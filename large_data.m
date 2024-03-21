clear all; close all; clc


% Open the HDF5 file
file_path = '20231030.h5';
file_info = h5info(file_path);

% Specify dataset to read
dataset_path = '/data';
dataset_info = h5info(file_path, dataset_path);

% Define chunk size (adjust as needed)
chunk_size = [414, 100000]; % Rows x Columns

% Preallocate memory for the entire dataset
data = zeros([dataset_info.Dataspace.Size(1),dataset_info.Dataspace.Size(3)], 'like', h5read(file_path, dataset_path));

sample_times = h5read("20231030.h5",'/sample_times');
[levels, length] = size(data);
dateNumbers = sample_times / (60*60*24) + datenum(1970,1,1);
% Read data in chunks
for i = 1:chunk_size(1):dataset_info.Dataspace.Size(1)
    for j = 1:chunk_size(2):dataset_info.Dataspace.Size(3)
        rows = i:min(i+chunk_size(1)-1, dataset_info.Dataspace.Size(1));
        cols = j:min(j+chunk_size(2)-1, dataset_info.Dataspace.Size(3));
        % Read data chunk
                % Specify start and count parameters as double arrays
        start = [rows(1), 1, cols(1)];
        count = [numel(rows), 1, numel(cols)];
        
        % Read data chunk
        data(rows, cols) = h5read(file_path, dataset_path, start, count);
    end
end







imagesc(data);

% Adjusting x-axis tick labels and ticks
numTicks = numel(dateNumbers);
ticksToDisplay = linspace(1, numTicks, 10); 
xticks(ticksToDisplay);
xticklabels(datestr(dateNumbers(round(ticksToDisplay)), 'yyyy-mm-dd HH:MM:SS'));
colormap('jet'); 
colorbar; % Add colorbar to indicate intensity
title('Shoe-based Sensor Data Heatmap');
xlabel('Samples');
ylabel('Levels');
