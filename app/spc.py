import statistics

def calculate_spc(values, tol_plus, tol_minus, target):

    values = [float(v) for v in values]

    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)

    usl = target + tol_plus
    lsl = target - tol_minus

    cp = (usl - lsl) / (6 * std_dev)

    cpu = (usl - mean) / (3 * std_dev)
    cpl = (mean - lsl) / (3 * std_dev)

    cpk = min(cpu, cpl)

    return {
        "mean": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "cp": round(cp, 3),
        "cpk": round(cpk, 3)
    }
