# Running Dinner
In this project, the organization of a running dinner is optimized, in which different groups participate, each of which hosts an event (appetizer, main course, dessert).
If a group does not host an event, it visits another group.
The maximum travel time between consecutive events should be minimized.

## Problem Instance
A problem instance consists of a set of groups $G$ and a set of places $V$, where these sets are usually identical since the groups themselves are hosts.
There should be exactly $k$ groups at the same location for an event.
In addition, there is a set of events $E$ consisting of a start event, end event and usually three events in between, namely appetizer, main course and dessert.
To minimize the maximum travel time between the events, the travel time $d_{v, w}$ between each pair of locations $v$, $w$ is also required.
<div align="center">
  
Parameter | Description
---: | :---
$g \in G$ | set of groups where subsets meet at locations for events
$k \in \mathbb{N}$ | number of groups at the same location for an event
$v \in V$ | set of locations
$v_g$ | home location of group $g$
$e \in E$ | set of events
$d_{v, w} \in \mathbb{R}_{\ge 0}$ | distance between locations $v$ and $w$
$P_1, P_2, P_3 \in \mathbb{R}_{\ge 0}$ | cost for different kind of penalties
  
</div>

## Mixed-Integer Programming Problem
The problem is formulated as a mixed-integer programming problem to be solved later by calling a solver from Python.

### Variables
Variable $x$ assigns groups to locations for events.
Variable $y$ stores the travel times of the individual groups between the events.
Variable $t$ specifies the times of the events, which depend on the travel times of the groups.
The remaining variables are auxiliary variables.
Variable $z$ checks whether two groups meet at an event.
The $p$ variables are relevant for possible penalty costs and store whether there are too few or too many groups at the same location for an event and whether some groups meet more than once.
<div align="center">
  
Variable | Description
---: | :---
$x_{g, v, e} \in \lbrace 0, 1\rbrace$ | Is group $g$ at location $v$ for event $e$?
$y_{g, v, w, e} \in \lbrace 0, 1\rbrace$ | Does group $g$ go from location $v$ to location $w$ after event $e$?
$t_e \in \mathbb{R}_{\ge 0}$ | start time of event $e$
$z_{g_1, g_2, v, e} \in \lbrace 0, 1\rbrace$ | Do groups $g_1$ and $g_2$ meet at location $v$ for event $e$?
$p^{1}_{v, e} \in \lbrace 0, 1\rbrace$ | Are there $k-1$ groups at location $v$ for event $e$?
$p^{2}_{v, e} \in \lbrace 0, 1\rbrace$ | Are there $k+1$ groups at location $v$ for event $e$?
$p^{3}_{g_1, g_2} \in \lbrace 0, 1\rbrace$ | Do groups $g_1$ and $g_2$ meet more than once?

</div>

### Objective
```math
\begin{equation}
\min\sum_{e \in E} t_e
\end{equation}
```

```math
\begin{equation}
\min\sum_{e \in E} t_e + \sum_{v \in V} \sum_{e \in E} \left( P_1 p^{1}_{v, e} + P_2 p^{2}_{v, e} \right) + \sum_{g_1 \in G} \sum_{g_2 \in G} P_3 p^{3}_{g_1, g_2}
\end{equation}
```

### Constraints

$$
\begin{equation}
x_{g, v, e} = 1 \Leftrightarrow \text{group $g$ is at location $v$ at event $e$}
\end{equation}
$$
