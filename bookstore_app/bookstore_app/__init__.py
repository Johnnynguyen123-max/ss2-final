import pymysql

# Giả lập thư viện MySQLdb
pymysql.install_as_MySQLdb()

# Đánh lừa Django về phiên bản của driver
pymysql.version_info = (2, 2, 1, "final", 0)