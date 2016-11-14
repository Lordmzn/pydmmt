% from M. Gatto and R. Casagrandi "Dispense del corso di Ecologia" (2003).
% Leslie matrix.
% Initial conditions: n1 = 40, n2 = 0, n3 = 20
% expected output: N[11] = 8.758826106880001e+02, AB[11] = 1.333728647970054


n1 = 40;
n2 = 0;
n3 = 20;
N = n1 + n2 + n3;
AB = nan;
for t = 1:10
    n1(t+1) = 1.6 * n2(t) + 1.2 * n3(t);
    n2(t+1) = 0.8 * n1(t);
    n3(t+1) = 0.7 * n2(t);
    N(t+1) = n1(t+1) + n2(t+1) + n3(t+1);
    AB(t+1) = N(t+1) / N(t);
end


%%
% expected output: N[11] = 3264.85815961600, AB[11] = 1.30176322373759
clear all

i1 = [12 11 34 54 68 51 23 -12 -25 -26 -123 -234]; 
i2 = [0 4 3 24 31 54 0 64 12 35 -64 -22];
i3 = [0 0 6 54 12 32 35 0 2 -2 -76 -24];

n1 = 40;
n2 = 0;
n3 = 20;
N = n1 + n2 + n3;
AB = nan;
for t = 1:10
    n1(t+1) = 1.6 * n2(t) + 1.2 * n3(t) + i1(t);
    n2(t+1) = 0.8 * n1(t) + i2(t);
    n3(t+1) = 0.7 * n2(t) + i3(t);
    N(t+1) = n1(t+1) + n2(t+1) + n3(t+1);
    AB(t+1) = N(t+1) / N(t);
end