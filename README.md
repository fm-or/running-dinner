# Running Dinner
In this project, the organization of a running dinner is optimized, in which different groups participate, each of which hosts an event (appetizer, main course, dessert).
If a group does not host an event, it visits another group.
The maximum travel time between consecutive events should be minimized.

## Problem Instance
A problem instance consists of a set of groups $G$ and a set of places $V$, where these sets are usually identical since the groups themselves are hosts.
There should be exactly $k$ groups at the same location for an event.
In addition, there is a set of events $E$ consisting of a start event $0$, end event $n+1$ and usually three main events in between, namely appetizer, main course and dessert.
To minimize the maximum travel time between the events, the travel time $d_{v, w}$ between each pair of locations $v$, $w$ is also required.
<div align="center">
  
Parameter | Description
---: | :---
$g \in G$ | set of groups where subsets meet at locations for events
$k \in \mathbb{N}$ | number of groups at the same location for an event
$v \in V$ | set of locations
$v_g \in V$ | home location of group $g$
$e \in \lbrace 0, \ldots, n+1 \rbrace = E $ | set of events
$e_g \in E$ | event where group $g$ is a host
$d_{v, w} \in \mathbb{R}_{\ge 0}$ | distance between locations $v$ and $w$
$P_1, P_2, P_3 \in \mathbb{R}_{\ge 0}$ | cost for different kind of penalties
  
</div>

## Mixed-Integer Programming Problem
The problem is formulated as a mixed-integer programming problem to be solved later by calling a solver from Python through [PuLP](https://github.com/coin-or/pulp).
See [Variables](#variables), [Objective](#objective) and [Constraints](#constraints) for the model and ... for the implementation.

### Variables
Variable $x$ assigns groups to locations for events.
Variable $t$ specifies the maximum travel times between events, which depend on the individual travel times of the groups.
The remaining variables are auxiliary variables.
Variable $y$ checks whether two groups meet at an event.
The $z$ variables are relevant for possible penalty costs and store whether there are too few or too many groups at the same location for an event and whether some groups meet more than once.
<div align="center">
  
Variable | Description
---: | :---
$x_{g, v, e} \in \lbrace 0, 1\rbrace$ | Is group $g$ at location $v$ for event $e$?
$t_e \in \mathbb{R}_{\ge 0}$ | maximum travel time from event $e$ to the next event
$y_{g, g', v, e} \in \lbrace 0, 1\rbrace$ | Do groups $g$ and $g'$ meet at location $v$ for event $e$?
$z^{1}_{v, e} \in \lbrace 0, 1\rbrace$ | Are there $k-1$ groups at location $v$ for event $e$?
$z^{2}_{v, e} \in \lbrace 0, 1\rbrace$ | Are there $k+1$ groups at location $v$ for event $e$?
$z^{3}_{g, g'} \in \lbrace 0, 1\rbrace$ | Do groups $g$ and $g'$ meet more than once?

</div>

### Objective
The aim is to minimize the maximum travel times between events in order to enable an efficient process.
Since the individual events are of equal value, an unweighted sum of the maximum travel times between the events can be used.
```math
\min \sum_{e = 0}^n t_e
```

The penalty cost for relaxing some constraints can be added to the objective function.
This is done in the form of a weighted sum with the weights $P_1$, $P_2$ and $P_3$ defined above.
```math
\min\ \sum_{e = 0}^n t_{e} + P_1 \cdot \sum_{v \in V} \sum_{e \in E} z^{1}_{v, e} + P_2 \cdot \sum_{v \in V} \sum_{e \in E} z^{2}_{v, e} + P_3 \cdot \sum_{g \in G} \sum_{g' \in G} z^{3}_{g, g'}
```

### Constraints
- First, the main variables $x$ and $t$ must be linked by the constraints.
The variables $x$ are influenced by other constraints and in turn provide the necessary lower bound on the maximum travel times in the objective function.
The maximum travel time between consecutive events is an upper bound on the travel times of the groups between the locations they visit at these events.
```math
d_{v, w} \cdot (x_{g, v, e} + x_{g, w, e+1} - 1) \le t_e \qquad \forall g \in G, v \in V, w \in V, e \in \lbrace 0, \ldots, n \rbrace
```

- The structure of the problem is mainly given by constraints on the variables $x$.
Each group must be in exactly one location for each event.
```math
\sum_{v \in V} x_{g, v, e} = 1 \qquad g \in G, e \in E
```

- Each group can visit each location no more than once during the main events.
```math
\sum_{e = 1}^n x_{g, v, e} \le 1 \qquad \forall g \in G, v \in V
```

- Each group starts at its home location.
```math
x_{g, v_g, 0} = 1 \qquad \forall g \in G
```

- Each group is at its home location when it hosts.
```math
x_{g, v_g, e_g} = 1 \qquad \forall g \in G
```
<ul>
  <li>There are two options for the final event.</li>
  <ul>
    <li>Either each group goes back to its home location.</li>
  </ul>
</ul>

```math
x_{g, v_g, n+1} = 1 \qquad \forall g \in G
```
<ul>
  <ul>
    <li>Or all the groups meet up for a joint party at a special location $v_s$. The special location may not be used for any other event.</li>
  </ul>
</ul>

```math
x_{g, v_s, n+1} = 1 \qquad \forall g \in G
```
```math
x_{g, v_s, e} = 0 \qquad \forall g \in G, e \in \lbrace 0, \ldots, n \rbrace
```

- If a group is hosting an event, three groups must be present.
Any deviation in either direction will result in a penalty.
```math
\sum_{g' \in G} x_{g', v_g, e} = 3 \cdot x_{g, v_g, e_g} - p^{1}_{v_g, e} + p^{2}_{v_g, e} \qquad \forall g \in G
```

- All locations that are not being used for an event cannot be visited.
```math
x_{g', v_g, e} = 0 \qquad \forall g, g' \in G, e \in E \setminus \lbrace e_g \rbrace
```
# ToDo:


when a team is not at home at a given position, there can be no other team
```math
\sum_{g' \in G} x_{g', v_g, e} \le 4 \cdot x_{g, v_g, e} \qquad \forall g \in G, e \in E
```

check if two teams are at the same place at the same time (except the last event)
```math
x_{g, v, e} + x_{g', v, e} \le 1 + z_{g, g', v, e} \qquad \forall g \ne g' \in G, v \in V, e \in \lbrace e_1, \ldots, e_n \rbrace
```

check that two teams can only meet once (except the last event)
```math
\sum_{v \in V} \sum_{i = 1}^{n-1} z_{g, g', v, e_i} \le 1 + p^{3}_{g, g'} \qquad g \ne g' \in G
```
