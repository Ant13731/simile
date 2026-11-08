Consider a visitor information system for managing a conference site. The system has to support the following operations:

- createMeeting: create a new meeting.
- cancelMeeting: delete meeting, provided no dining room, conference rooms, and visitors are associated with that meeting.
- cancelMeetingArrangement: delete meeting with all associated rooms and visitors.
- enterVisitor: create a new visitor entry.
- removeVisitor: remove visitor from the system.
- addVisitorToMeeting, removeVisitorFromMeeting: as the name says.
- bookDiningRoom, cancelDiningRoom: for a particular meeting.
- bookConferenceRoom, cancelConferenceRoom: for a particular meeting.

```python
module VisitorInformationSystem

var visitors: set Visitor := ∅

var meetings: set Meeting := ∅
var attends:Visitor ↛ Meeting := ∅ – partial function
var convenes: Meeting ↔︎ ConferenceRoom := ∅ – relation
var eats: Meeting ↛ DiningRoom := ∅

{invariant:
(dom attends ⊆ visitors) ∧ (ran attends ⊆ meetings) ∧
(dom convenes ⊆ meetings) ∧ injective(convenes) ∧ (dom eats ⊆ meetings)}

procedure createMeeting(m : Meeting)
    if m ∉ meetings then meetings := meetings ⋃ {m}
    else print(“meeting exists”)

procedure cancelMeeting(m : Meeting)
    if m ∈ meetings ∧ m ∉ ran attends ∧ m ∉ dom convenes ∧ m ∉ dom eats then
        meetings := meetings – {m}
    else print(“meeting cannot be cancelled”)

procedure cancelMeetingArrangement(m : Meeting)
    if m ∈ meetings then
        meetings, attends, convenes, eats := meetings ∖ {m}, attends ⩥ {m}, convenes ⩤ {m}, eats ⩤ {m}
    else print(“meeting does not exist”)

procedure enterVisitor(v : Visitor)
    if v ∉ visitors then visitors := visitors ∪ {v}
    else print(“visitor exists”)

procedure removeVisitor(v: Visitor)
    if v ∈ visitors ∧ v ∈ dom attends then visitors := visitors – {v}
    else print(“visitor cannot be removed”)

procedure addVisitorToMeeting (v : Visitor, m : Meeting)
    if v ∈ visitors ∧ m ∈ meetings ∧ v ∉ dom attends then attends(v) := m
    else print(“visitor cannot be added”)

procedure removeVisitorFromMeeting (v : Visitor)
    if v ∈ dom attends then attends := attends ⩤ {v}
    else print(“visitor cannot be removed”)

procedure visitorInfo(v: Visitor)
    if v ∈ dom attends then print(attends(v))
    else if v ∈ visitors then print(“visitor not attending meeting”)
    else print(“visitor not registered”)

procedure bookDiningRoom(m : Meeting, d : DiningRoom)
    if m ∉ dom eats then eats (m) := d
    else print(“dining room cannot be booked”)

procedure cancelDiningRoom(m : Meeting)
    if m ∈ dom eats then eats := eats ⩤ {m}
    else print(“dining room cannot be cancelled”)

procedure bookConferenceRoom(m : Meeting, c : ConferenceRoom)
    if m ∈ meetings ∧ c ∉ ran convenes then
        convenes := convenes ∪ {m ↦ c}
    else print(“meeting cannot be booked”)

procedure cancelConferenceRoom (c : ConferenceRoom)
    if c ∈ ran convenes then convenes := convenes ⩥ {c}
    else print(“conference room cannot be cancelled”)

procedure conferenceRooms (m : Meeting)
    if m ∈ meetings then
        print(“conference rooms:”) ;
        for c ∈ convenes [{m}] do print(c)
    else print(“no such meeting”)

procedure diningRooms (m : Meeting)
    if m ∈ meetings then
        if m ∈ dom eats then print(eats(m)) else print(“no dining room”)
    else print(“no such meeting”)

procedure diningRoomOccupancy(d : DiningRoom)
    print(card((eats⁻ ¹ ◦ attends⁻ ¹)[{d}]))
```

# Derivation of SYNT Rewrite Rules applied to `diningRoomOccupancy`

The SYNT abstract replaces `eats` with `location`, so that is what we will be using here.

<!-- $$
\begin{align*}
&card((location^{-1} \circ attends^{-1})[\{room\}])\\
\rightarrow & \sum 1 \cdot x \in (location^{-1} \circ attends^{-1})[\{room\}]\\
\rightarrow & \sum 1 \cdot x \in \{b \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a \in \{room\}\}\\
\rightarrow & \sum 1 \cdot x \in \{b \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\}\\
\rightarrow & \sum 1 \cdot x \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\\
\rightarrow &\\
\rightarrow & \sum 1 \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\\
\rightarrow & \sum 1 \cdot a \mapsto c \in location^{-1} \land c \mapsto b \in attends^{-1} \mid a = room\\
\rightarrow & \sum 1 \cdot c \mapsto a \in location \land b \mapsto c \in attends \mid a = room\\
\end{align*}
$$ -->

$$
\begin{align*}
&card((location^{-1} \circ attends^{-1})[\{room\}])\\
\rightarrow & \sum 1 \cdot x \in (location^{-1} \circ attends^{-1})[\{room\}]\\
\rightarrow & \sum 1 \cdot x \in \{b \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a \in \{room\}\}\\
\rightarrow & \sum 1 \cdot x \in \{b \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\}\\
% NOTE: "eliminating" b in this fashion really only works because the parent enumeration (\sum 1) doesn't care about the exact value of b or a \mapsto b, just that some value exists
% \rightarrow & \sum 1 \cdot x \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\\
% \rightarrow & \text{Missing collapse of x and b?} \\
\rightarrow & \sum 1 \cdot a \mapsto b \in location^{-1} \circ attends^{-1} \mid a = room\\
\rightarrow & \sum 1 \cdot a \mapsto c \in location^{-1} \land c' \mapsto b \in attends^{-1} \mid a = room \land c = c'\\
\rightarrow & \sum 1 \cdot c \mapsto a \in location \land b \mapsto c' \in attends \mid a = room \land c = c'\\
\rightarrow &
% \begin{minipage}[]{.7\textwidth}
% \begin{algorithmic}
    % \State $c := 0$
    % \For{$c \mapsto a$ in $location$}
    %     \If{$b \mapsto c$ in $attends$ and $a = room$ and $c = c'$}
    %         \State $c := c + 1$
    %     \EndIf
    % \EndFor
% \end{algorithmic}
% \end{minipage}
\\
\rightarrow &
% \begin{minipage}[]{.7\textwidth}
% \begin{algorithmic}
    % \State $c := 0$
    % \For{$c \mapsto a$ in $location$}
    %     \If{$a = room$}
    %         \For{$b \mapsto c$ in $attends$}
    %             \If{$c = c'$}
    %                 \State $c := c + 1$
    %             \EndIf
    %         \EndFor
    %     \EndIf
    % \EndFor
% \end{algorithmic}
% \end{minipage}
\end{align*}
$$

Now from set notation to code portion
