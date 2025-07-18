#!/usr/bin/env python3
"""
USDC 트랜잭션 데이터 간단 분석 (pandas 없이)
"""

import csv
import statistics

def simple_gas_analysis():
    """CSV 파일에서 가스 데이터를 간단히 분석합니다."""
    
    gas_fees = []
    
    # CSV 파일 읽기
    with open('usdc_txs.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            gas_fee = float(row['Txn Fee'])
            gas_fees.append(gas_fee)
    
    print("🔍 USDC 트랜잭션 가스비 분석 결과:")
    print("=" * 50)
    
    # 기본 통계
    print(f"📊 총 트랜잭션 수: {len(gas_fees)}")
    print(f"💰 평균 가스비: {statistics.mean(gas_fees):.8f} ETH")
    print(f"📈 최대 가스비: {max(gas_fees):.8f} ETH")
    print(f"📉 최소 가스비: {min(gas_fees):.8f} ETH")
    print(f"🎯 중간값: {statistics.median(gas_fees):.8f} ETH")
    
    if len(gas_fees) > 1:
        print(f"📏 표준편차: {statistics.stdev(gas_fees):.8f} ETH")
    
    # 정렬 후 분위수 계산
    sorted_fees = sorted(gas_fees)
    n = len(sorted_fees)
    
    def percentile(data, p):
        index = int(p * len(data))
        if index >= len(data):
            index = len(data) - 1
        return data[index]
    
    print("\n📋 분포 분석:")
    print(f"25% 구간: {percentile(sorted_fees, 0.25):.8f} ETH")
    print(f"75% 구간: {percentile(sorted_fees, 0.75):.8f} ETH")
    print(f"95% 구간: {percentile(sorted_fees, 0.95):.8f} ETH")
    print(f"99% 구간: {percentile(sorted_fees, 0.99):.8f} ETH")
    
    # Wei 단위로 변환하고 가스 한도 추정
    print("\n⛽ 가스 한도 추정 (1 gwei 기준):")
    gwei_price = 10**9  # 1 gwei in wei
    
    # 가스 한도 = 가스비(wei) / 가스가격(wei)
    gas_limits = [(fee * 10**18) / gwei_price for fee in gas_fees]
    
    print(f"🔢 평균 가스 사용량: {statistics.mean(gas_limits):.0f}")
    print(f"📈 최대 가스 사용량: {max(gas_limits):.0f}")
    print(f"📉 최소 가스 사용량: {min(gas_limits):.0f}")
    
    sorted_limits = sorted(gas_limits)
    p95_gas = percentile(sorted_limits, 0.95)
    print(f"🎯 95% 안전 마진: {p95_gas:.0f}")
    
    # 권장 가스 한도 계산 (95% + 20% 여유분)
    recommended_gas_limit = int(p95_gas * 1.2)
    
    print("\n🎯 권장 설정:")
    print("=" * 30)
    print(f"권장 가스 한도: {recommended_gas_limit:,}")
    print(f"권장 가스 가격: 1 gwei")
    print(f"예상 가스비: {recommended_gas_limit * gwei_price / 10**18:.8f} ETH")
    
    # 현재 설정과 비교
    current_gas = 60000
    current_cost = current_gas * gwei_price / 10**18
    
    print(f"\n🔄 현재 봇 설정 비교:")
    print(f"현재 가스 한도: {current_gas:,}")
    print(f"현재 가스비: {current_cost:.8f} ETH")
    
    if current_gas >= recommended_gas_limit:
        print("✅ 현재 설정이 충분합니다!")
        margin = ((current_gas / recommended_gas_limit) - 1) * 100
        print(f"   {margin:.1f}% 여유분이 있습니다.")
    else:
        print("⚠️  현재 설정이 부족할 수 있습니다!")
        shortage = ((recommended_gas_limit / current_gas) - 1) * 100
        print(f"   {shortage:.1f}% 더 필요합니다.")
    
    # 다양한 가스 가격별 비용 분석
    print(f"\n💡 다양한 가스 가격별 예상 비용 (권장 한도 기준):")
    eth_price = 3200  # ETH 가격 가정
    for gwei in [0.5, 1, 2, 5]:
        cost_eth = recommended_gas_limit * (gwei * 10**9) / 10**18
        cost_usd = cost_eth * eth_price
        print(f"{gwei:3.1f} gwei: {cost_eth:.8f} ETH (${cost_usd:.4f})")
    
    # 현재 잔고로 가능한 트랜잭션 수
    current_balance = 0.001915  # ETH
    current_tx_cost = current_gas * gwei_price / 10**18
    recommended_tx_cost = recommended_gas_limit * gwei_price / 10**18
    
    print(f"\n💰 현재 잔고 ({current_balance} ETH)로 가능한 트랜잭션 수:")
    print(f"현재 설정: {int(current_balance / current_tx_cost)}회")
    print(f"권장 설정: {int(current_balance / recommended_tx_cost)}회")
    
    return {
        'recommended_gas_limit': recommended_gas_limit,
        'mean_gas_used': int(statistics.mean(gas_limits)),
        'max_gas_used': int(max(gas_limits)),
        'p95_gas_used': int(p95_gas),
        'total_transactions': len(gas_fees)
    }

if __name__ == "__main__":
    result = simple_gas_analysis()
    print(f"\n📋 분석 요약:")
    print(f"총 {result['total_transactions']}개 트랜잭션 분석")
    print(f"권장 가스 한도: {result['recommended_gas_limit']:,}") 