import requests
import json


"""
	Documentation for the graph=ql: https://api.developer.monday.com/docs/items-queries
"""


class WorkSpace():
	"""
		A workspace.
	"""
	
	def __init__(self, token):
		"""
			Define the workspace.
		"""
	
		# The token of the Monday user.
		self.token = token
		
		# The link of the most recent api.
		self.apiUrl = "https://api.monday.com/v2"
		
		# Headers for the post requests.
		self.headers = {"Authorization" : self.token}
		
		# A dictionary with all the boards in the workspace {board_name: board instance}.
		self.boards = {}
		
		# Update the boards list to match the current status of boards in the workspace.
		self.update_boards_in_ws()

		# Get the id of the workspace.
		self.work_space_id = self.get_ws_id()
	
	def post_request(self, query):
		"""
			The function receives a graph-ql query, sends a post request to the monday user with the ws token. It returns the response as a string.
		"""
		
		# Follow the format.
		data = {'query': query}
		
		print("sending:", query)
		
		# Send the post request and save the response as the received json string.
		response_str = requests.post(url=self.apiUrl, json=data, headers=self.headers).text

		# Convert the json string to the original object.
		response = json.loads(response_str)

		# Return the answer.
		try:
			print("received:", response)
			print()
			return response['data']
		
		except:
			
			# Probably an error.
			print("error: ", response)
			print()
	
	def get_ws_id(self):
		"""
			The function returns the id of the workspace.
		"""
		
		return self.post_request(query='{ boards (ids: ' + list(self.boards.values())[0].board_id + ') { id name workspace { id name } }}')['boards'][0]['workspace']['id']
	
	def update_boards_in_ws(self):
		"""
			The function extracts the currently existing boards in the workspace.
			It creates for each board, a Board instance and initializes it.
			It returns a list with all the boards.
		"""
		
		# Get the data of the boards with graph-ql format.
		boards_data = self.post_request(query='{ boards (limit:1) {id name groups{id title} columns{id title type description} items{id name group{ id title } column_values{id text}} }}')
		
		# Get the list of boards, as a dictionary converted from json.
		boards_json_list = boards_data['boards']

		# This list will eventual contain all the boards in the workspace.
		self.boards = {}
		
		# Iterate over the boards.
		for board in boards_json_list:
			
			# Create the current board and append it the the boards list.
			self.boards[board["name"]] = Board(ws=self, name=board['name'], board_id=board['id'], json_groups=board['groups'], json_columns=board['columns'], json_items=board['items'])
	
	def add_board(self, board):
		"""
			The function receives a board and adds it to the workspace.
		"""
		
		self.boards[board.name] = board
		

class Board():
	"""
		Represents a board in a work_space.
	"""
	
	def __init__(self, ws, name, json_groups=None, json_columns=None, json_items=None, board_id=None):
		"""
			Create an instance to an existing board.
		"""
		
		# The work_space of the board.
		self.work_space = ws
		
		# The name of the board, its title.
		self.name = name
		
		# A dictionary with all the columns of the board {column title: column instance}.
		self.columns = {}
		
		# A dictionary with all the groups of the board {group title: group instance}.
		self.groups = {}
		
		# This board is already on monday, get its values from monday.
		if json_groups:
		
			# The id of the board, used for identifying the board with the api.
			self.board_id = board_id

			# Set the columns of the board.
			self.set_columns(json_columns)
			
			# Set the received groups as the groups of the board.
			self.set_groups(json_groups)
			
			# Set the received items.
			self.set_items(json_items)

		# Create the board on monday too.
		else:
		
			# Create the query.
			query = 'mutation { create_board (board_name: "' + self.name + '", board_kind: private, workspace_id: ' + str(self.work_space.work_space_id) + ') { id } }'
			
			# Update the board on monday and save its id.
			self.board_id = self.work_space.post_request(query)['create_board']['id']		 
			
			# Remove any default groups.
			for group in self.work_space.post_request(query='{ boards (ids: ' + self.board_id + ') {id groups{id title}} }')['boards'][0]['groups']:
				
				self.work_space.post_request(query='mutation { delete_group (board_id: ' + self.board_id + ', group_id: "' + group["id"] + '") { id deleted } }')
			
			# Add the board to the work_space.
			self.work_space.add_board(self)
	
	def set_columns(self, json_columns):
		"""
			The function receives a json list of columns. It creates and adds the columns to the board.
		"""
		
		# Iterate over the columns.
		for column in json_columns:
		
			# Create and append the current column.
			self.columns[column['title']] = Column(board=self, title=column['title'], description=column['description'], column_type=column['type'], column_id=column['id'])
	
	def set_groups(self, json_groups):
		"""
			The function receives a json list of groups. It creates and adds the groups to the board.
		"""
	
		# Iterate over the groups.
		for group in json_groups:
			
			# Create and append the current group.
			self.groups[group['title']] = Group(board=self, group_id=group['id'], title=group['title'])
			
	def set_items(self, json_items):
		"""
			The function receives a json list of items. It creates and adds the items to their groups.
		"""
		
		# Iterate over all the items in the board.
		for item in json_items:
			
			# The group of the item.
			item_group_title = item['group']['title']
			
			# Create the new item.
			new_item = Item(group=item_group_title, name=item['name'], item_id=item['id'], json_columns_values=item['column_values'])
			
			# Add it to the group.
			self.groups[item_group_title].add_item(new_item)
		
	def add_column(self, column):
		"""
			The function receives a column and adds it to the board.
		"""
		
		self.columns[column.title] = column
	
	def add_group(self, group):
		"""
			The function receives a group and adds it to the board.
		"""
		
		self.groups[group.title] = group
		

class Group():
	"""
		Represents a group of a board.
	"""
	
	def __init__(self, board, title, group_id=None):
		"""
			Initialize the group.
		"""
		
		# The board that the group is within.
		self.board = board
		
		# The title of the group.
		self.title = title
		
		# A list with all the items of the group.
		self.items = {}
		
		# The group already exists on monday, get its details.
		if group_id:

			# The id of the group.
			self.group_id = group_id
			
		# The group does not exist in monday.
		else:

			# Update it on monday.
			self.group_id = self.board.work_space.post_request(query='mutation { create_group (board_id: ' + self.board.board_id + ', group_name: "' + self.title + '") { id } }')['create_group']['id']
		
	def set_items(self, json_items):
		"""
			The function receives a json list of items. It creates and adds the items to the group.
		"""
		
		# If no items received, return an empty list.
		if not json_items:
			return []
		
		# The final list with the items instances.
		items = {}
		
		# Iterate over the items.
		for item in json_items:
			
			# Create the item and append it to the items list.
			items[item['name']] = Item(group=self, item_id=item['id'], name=item['name'])
			
		# Return the list of items.
		return items
		
	def get_id(self):
		"""
			The function returns the id of the group.
		"""

		# Get from monday the titles and ids of the groups.
		groups = self.board.work_space.post_request(query='{ boards (ids: ' + self.board.board_id + ') {id groups {id title}}}')['boards'][0]['groups']
		
		# Iterate over the groups of the board.
		for group in groups:
		
			# Locate the current group.
			if group['title'] == self.title:
			
				# And return its id.
				return group['id']
		
		# The group for some reason is not on the board.
		return ''
		
	def add_item(self, item):
		"""
			The function receives an item and adds it to the group.
		"""
		
		self.items[item.name] = item


class Column():
	"""
		Represents a column of a board.
	"""
	
	def __init__(self, board, title, description, column_type, column_id=None):
		"""
			Initialize the column.
		"""
		
		# The board of the column.
		self.board = board
		
		# The title of the column.
		self.title = title
		
		# The description of the column.
		self.description = description
		
		# The type of the column.
		self.column_type = column_type
		
		# The column already exists in monday.
		if column_id:
		
			self.column_id = column_id

		# Create the column in monday.
		else:

			self.column_id = self.board.work_space.post_request(query='mutation{ create_column(board_id: ' + self.board.board_id + ', title:"' + self.title + '", description: "' + self.description + '", column_type:' + self.column_type + ') { id title description } }')['create_column']['id']
		

class Item():
	"""
		Represents an item of a group.
	"""
	
	def __init__(self, group, name, item_id=None, json_columns_values=None, columns_values=[]):
		"""
			Initialize the item.
			Note: One of json_column_values or column_values must be specified. column_values is of the form: [(column title, value)].
		"""
		
		# The group the item is within.
		self.group = group
		
		# The id of the item.
		self.item_id = item_id
		
		# name of the item
		self.name = name
		
		# The columns values of the item {column id: item's value}.
		self.columns_values = {}

		# The item already exists in monday.
		if item_id:

			# Save its id.
			self.item_id = item_id

			# Extract its column values.
			self.set_columns(json_columns_values)

		# Update the item in monday.
		else:

			# Convert the columns values to json format, as monday wants.
			columns_values_json = '{' + ', '.join('\\\"' + self.group.board.columns[column_title].column_id + '\\\": \\\"' + value + '\\\"' for column_title, value in columns_values) + '}'

			# Add the item to monday and save its id.
			self.item_id = self.group.board.work_space.post_request(query='mutation {create_item (board_id: ' + self.group.board.board_id + ', group_id: "' + self.group.group_id + '", item_name: "' + self.name + '", column_values: "' + columns_values_json + '") { id } }')['create_item']['id']

	def set_columns(self, json_columns_values):
		"""
			The item is already in monday. The function receives its columns values and saves them.
		"""
		
		# Iterate over the columns values.
		for column_value in json_columns_values:
			
			# Save the column id and its value.
			self.columns_values[column_value['id']] = column_value['text']
			
	def upload_files(self, column_title, files_paths):
		"""
			The function receives a list with files paths and a column and uploads the file to that column.
		"""
		for file_path in files_paths:
		
			# The query that makes the request to upload the file to the specific received column.
			query = 'mutation ($file: File!) { add_file_to_column (file: $file, item_id: ' + self.item_id + ', column_id: "' + self.group.board.columns[column_title].column_id + '") {id }}'

			# A list with all the files in the required format.
			files=[('variables[file]', (file_path ,open(file_path, 'rb'), 'multipart/form-data'))]
		
			# Follow the format.
			data = {'query': query}
			
			print("sending:", query)

			# Send the post request and save the response as the received json string.
			response_str = requests.post(url="https://api.monday.com/v2/file", headers={'Authorization': self.group.board.work_space.token}, data=data, files=files).text

			# Convert the json string to the original object.
			response = json.loads(response_str)
			
			print("response:", response)
		
"""

	Usage:
	
	# First, you'd probably like to create a reference to your workspace.
	work_space = WorkSpace(token="your token")
	
	# Now you can create boards.
	my_board = Board(ws=work_space, name="My terrific board")
	
	# And you can create columns to the board.
	my_board.add_column(Column(board=my_board, title="Date", description="When the row was added to the board", column_type="date"))
	my_board.add_column(Column(board=my_board, title="Favourite color", description="the favourite color of the row", column_type="text"))
	my_board.add_column(Column(board=my_board, title="Attached Files", description="", column_type="file"))
	
	# These columns are saved in my_board.columns. This is a dictionary of the form: {column title: column instance}.
	
	# And you can create groups.
	my_board.add_group(Group(board=my_board, title="An amazing group"))
	my_board.add_group(Group(board=my_board, title="Another amazing group"))
	
	# These groups are saved in my_board.groups. This is a dictionary of the form: {group title: group instance}.
	
	# Now you can add items to groups.
	my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 1"))
	my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 2"))
	
	# These items are saved in my_board.groups["An amazing group"].items. This is a dictionary of the form: {item name: item instance}.
	
	# You can upload a file to an item's column.
	my_board.groups["An amazing group"].items["Spectacular item 1"].upload_files(column_title="Attached Files", files_paths=["path_to_local_file1", "path_to_local_file2"])

"""

# Create the workspace.
work_space = WorkSpace(token="eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjE1ODI2MDM3MiwidWlkIjoyOTk1NzM5MSwiaWFkIjoiMjAyMi0wNC0yOVQyMTo0NzozNi4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTE4NzU5MjIsInJnbiI6InVzZTEifQ.R7UplEfmGyfk1uPEr1A-UFNlcdCZ8VjfrGKl63WQYYo")

# --- Courses Board ---

# Create a new board for the courses.
courses_board = Board(ws=work_space, name="Courses")

# Create columns for the courses board.
courses_board.add_column(Column(board=courses_board, title="From", description="Who sent the mail", column_type="text"))
courses_board.add_column(Column(board=courses_board, title="Date", description="When the email was received", column_type="date"))
courses_board.add_column(Column(board=courses_board, title="Attached Files", description="All the files attached to this mail", column_type="file"))

# Create a group for each course in courses.
for course in ["Calculus", "Linear Algebra", "Combinatorics"]:

	# Create a group for the current course.
	courses_board.add_group(Group(board=courses_board, title=course))

# Add mails to each group.
courses_board.groups["Calculus"].add_item(Item(group=courses_board.groups["Calculus"], name="mail 1", columns_values=[("From", "Moshe"), ("Date", "2022-05-03")]))
courses_board.groups["Calculus"].add_item(Item(group=courses_board.groups["Calculus"], name="mail 2", columns_values=[("From", "Shalom"), ("Date", "2022-05-04")]))
courses_board.groups["Calculus"].add_item(Item(group=courses_board.groups["Calculus"], name="mail 3", columns_values=[("From", "Yisaschar"), ("Date", "2022-05-07")]))
courses_board.groups["Combinatorics"].add_item(Item(group=courses_board.groups["Combinatorics"], name="mail 1"))
courses_board.groups["Linear Algebra"].add_item(Item(group=courses_board.groups["Linear Algebra"], name="mail 2"))
courses_board.groups["Linear Algebra"].add_item(Item(group=courses_board.groups["Linear Algebra"], name="mail 2"))

# Add the attached files to the mails.
courses_board.groups["Calculus"].items["mail 1"].upload_files(column_title="Attached Files", files_paths=['C:\python\MondayHackathon\hello world.txt', 'C:\python\MondayHackathon\Just another file.txt'])


"""
# --- Links Board ---

# Create a new board for the links.
links_board = Board(ws=work_space, name="Links")

# Create columns for the links board.
links_board.add_column(Column(board=links_board, title="Subject", description="", column_type="text"))
links_board.add_column(Column(board=links_board, title="From", description="Who sent the mail", column_type="text"))
links_board.add_column(Column(board=links_board, title="Date", description="When the email was received", column_type="date"))

# Create a group for each period.
for period in ["Last Week", "Last Month", "Last 3 Months", "Last Year", "All Time"]:

	# Create a group for the current period.
	links_board.add_group(Group(board=links_board, title=period))

# Add mails to each group.
links_board.groups["All Time"].add_item(Item(group=links_board.groups["All Time"], name="link 1"))
links_board.groups["All Time"].add_item(Item(group=links_board.groups["All Time"], name="link 2"))
links_board.groups["Last Year"].add_item(Item(group=links_board.groups["Last Year"], name="link 1"))
links_board.groups["Last Year"].add_item(Item(group=links_board.groups["Last Year"], name="link 2"))
links_board.groups["Last 3 Months"].add_item(Item(group=links_board.groups["Last 3 Months"], name="link 1"))
links_board.groups["Last 3 Months"].add_item(Item(group=links_board.groups["Last 3 Months"], name="link 2"))
links_board.groups["Last Month"].add_item(Item(group=links_board.groups["Last Month"], name="link 1"))
links_board.groups["Last Month"].add_item(Item(group=links_board.groups["Last Month"], name="link 2"))
links_board.groups["Last Week"].add_item(Item(group=links_board.groups["Last Week"], name="link 1"))
links_board.groups["Last Week"].add_item(Item(group=links_board.groups["Last Week"], name="link 2"))


# --- Attached Files Board ---

# Create a new board for the courses.
attached_files_board = Board(ws=work_space, name="Attached Files")

# Create columns for the attached files board.
attached_files_board.add_column(Column(board=attached_files_board, title="Subject", description="", column_type="text"))
attached_files_board.add_column(Column(board=attached_files_board, title="From", description="Who sent the mail", column_type="text"))
attached_files_board.add_column(Column(board=attached_files_board, title="Date", description="When the email was received", column_type="date"))

# Create a group for each period.
for period in ["Last Week", "Last Month", "Last 3 Months", "Last Year", "All Time"]:

	# Create a group for the current period.
	attached_files_board.add_group(Group(board=attached_files_board, title=period))

# Add mails to each group.
attached_files_board.groups["All Time"].add_item(Item(group=attached_files_board.groups["All Time"], name="attached file 1"))
attached_files_board.groups["All Time"].add_item(Item(group=attached_files_board.groups["All Time"], name="attached file 2"))
attached_files_board.groups["Last Year"].add_item(Item(group=attached_files_board.groups["Last Year"], name="attached file 1"))
attached_files_board.groups["Last Year"].add_item(Item(group=attached_files_board.groups["Last Year"], name="attached file 2"))
attached_files_board.groups["Last 3 Months"].add_item(Item(group=attached_files_board.groups["Last 3 Months"], name="attached file 1"))
attached_files_board.groups["Last 3 Months"].add_item(Item(group=attached_files_board.groups["Last 3 Months"], name="attached file 2"))
attached_files_board.groups["Last Month"].add_item(Item(group=attached_files_board.groups["Last Month"], name="attached file 1"))
attached_files_board.groups["Last Month"].add_item(Item(group=attached_files_board.groups["Last Month"], name="attached file 2"))
attached_files_board.groups["Last Month"].add_item(Item(group=attached_files_board.groups["Last Month"], name="attached file 3"))
attached_files_board.groups["Last Week"].add_item(Item(group=attached_files_board.groups["Last Week"], name="attached file 1"))
attached_files_board.groups["Last Week"].add_item(Item(group=attached_files_board.groups["Last Week"], name="attached file 2"))


# --- secretariat Board ---

# Create a new board for the secretariat.
secretariat_board = Board(ws=work_space, name="secretariat")

# Create columns for the secretariat board.
secretariat_board.add_column(Column(board=secretariat_board, title="Date", description="When the email was received", column_type="date"))
secretariat_board.add_column(Column(board=secretariat_board, title="Attached Files", description="Files attached to the mail", column_type="text"))


# Create a group for each period.
for period in ["Last Week", "Last Month", "Last 3 Months", "Last Year", "All Time"]:

	# Create a group for the current period.
	secretariat_board.add_group(Group(board=secretariat_board, title=period))

# Add mails to each group.
secretariat_board.groups["All Time"].add_item(Item(group=secretariat_board.groups["All Time"], name="mail  1"))
secretariat_board.groups["All Time"].add_item(Item(group=secretariat_board.groups["All Time"], name="mail  2"))
secretariat_board.groups["Last Year"].add_item(Item(group=secretariat_board.groups["Last Year"], name="mail  1"))
secretariat_board.groups["Last Year"].add_item(Item(group=secretariat_board.groups["Last Year"], name="mail  2"))
secretariat_board.groups["Last 3 Months"].add_item(Item(group=secretariat_board.groups["Last 3 Months"], name="mail  1"))
secretariat_board.groups["Last 3 Months"].add_item(Item(group=secretariat_board.groups["Last 3 Months"], name="mail  2"))
secretariat_board.groups["Last Month"].add_item(Item(group=secretariat_board.groups["Last Month"], name="mail  1"))
secretariat_board.groups["Last Month"].add_item(Item(group=secretariat_board.groups["Last Month"], name="mail  2"))
secretariat_board.groups["Last Month"].add_item(Item(group=secretariat_board.groups["Last Month"], name="mail  3"))
secretariat_board.groups["Last Week"].add_item(Item(group=secretariat_board.groups["Last Week"], name="mail  1"))
secretariat_board.groups["Last Week"].add_item(Item(group=secretariat_board.groups["Last Week"], name="mail  2"))
"""