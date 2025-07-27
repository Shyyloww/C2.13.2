import threading
from c2_server.web_server import run_server, data_queue
from c2_server.gui.main_window import App

if __name__ == "__main__":
    # Run the Flask web server in a separate thread
    # The 'daemon=True' ensures the thread will close when the main app closes
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Create and run the main GUI application
    app = App(data_queue=data_queue)
    app.mainloop()