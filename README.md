#### What does Uber Adventure do?
Uber Adventure is a mobile webapp takes your current location and returns a cool place you can reach with Uber given a certain amount of money (defaulted at $7). For the best experience please use this app on your phone web browser!

#### How I built Uber Adventure
I used the web development framework Flask, the Uber API, and the Yelp API to build this webapp. First, I use Uber's price scheme to determine how far (in meters) $x can take you with Uber. Second, I determine which Yelp destinations fall within the radius determined earlier that have a rating above 3.5/5 and fall into categories of interesting things (dancing, hiking, jazz clubs, etc.) Finally, I randomly select one of these destinations and present it to the user with a "request ride" deep link button that leads to the Uber app with all the trip information already filled in.
