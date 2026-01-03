import datetime
import uuid
import random

def generate_complex_logs(filename="extended_services.log", target_lines=990000):
    services = ["auth-service", "user-service", "payment-service", "inventory-service", 
                "notification-service", "shipping-service", "search-service", "deploy-service"]
    
    current_time = datetime.datetime(2026, 1, 3, 13, 55, 1)
    
    with open(filename, "w") as f:
        for i in range(target_lines):
            # Randomly pick a log type
            log_type = random.choice(["INFO", "WARN", "ERROR"])
            svc = random.choice(services)
            user_id = random.randint(1000, 9999)
            
            # Simple jump in time
            current_time += datetime.timedelta(seconds=random.randint(2, 45))
            ts = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            if svc == "auth-service":
                msg = f"{ts} INFO auth-service login success user_id={user_id}" if log_type != "ERROR" else f"{ts} ERROR auth-service brute_force_detected ip=192.168.1.{random.randint(1,255)}"
            elif svc == "payment-service":
                amt = random.choice([499, 1299, 2500, 50, 10]) / 100
                msg = f"{ts} INFO payment-service charge success user_id={user_id} amount={amt}" if log_type == "INFO" else f"{ts} ERROR payment-service failed charge uuid={uuid.uuid4()}"
            elif svc == "inventory-service":
                msg = f"{ts} INFO inventory-service stock_check status=in_stock product_id=sku-{random.randint(100,999)}"
            elif svc == "search-service":
                msg = f"{ts} INFO search-service query_executed query=\"item_{random.randint(1,10)}\" results={random.randint(0,100)}"
            else:
                msg = f"{ts} {log_type} {svc} operation_status=processed user_id={user_id}"

            f.write(msg + "\n")

    print(f"Generated {target_lines} lines in {filename}")

generate_complex_logs()
