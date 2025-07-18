#!/usr/bin/env python3
"""
USDC 트랜잭션 데이터 분석을 통한 최적 가스 한도 산출
"""

import pandas as pd
import numpy as np
from web3 import Web3

def analyze_gas_data():
    """CSV 파일에서 가스 데이터를 분석합니다."""
    
    # CSV 파일 읽기
    df = pd.read_csv('usdc_txs.csv')
    
    # 가스비 데이터 추출 (ETH 단위)
    gas_fees = df['Txn Fee'].astype(float)
    
    print("🔍 USDC 트랜잭션 가스비 분석 결과:")
    print("=" * 50)
    
    # 기본 통계
    print(f"📊 총 트랜잭션 수: {len(gas_fees)}")
    print(f"💰 평균 가스비: {gas_fees.mean():.8f} ETH")
    print(f"📈 최대 가스비: {gas_fees.max():.8f} ETH")
    print(f"📉 최소 가스비: {gas_fees.min():.8f} ETH")
    print(f"🎯 중간값: {gas_fees.median():.8f} ETH")
    print(f"📏 표준편차: {gas_fees.std():.8f} ETH")
    
    print("\n📋 분포 분석:")
    print(f"25% 구간: {gas_fees.quantile(0.25):.8f} ETH")
    print(f"75% 구간: {gas_fees.quantile(0.75):.8f} ETH")
    print(f"95% 구간: {gas_fees.quantile(0.95):.8f} ETH")
    print(f"99% 구간: {gas_fees.quantile(0.99):.8f} ETH")
    
    # Wei 단위로 변환
    w3 = Web3()
    gas_fees_wei = gas_fees * 10**18
    
    print("\n⛽ 가스 한도 추정 (1 gwei 기준):")
    gwei_price = 10**9  # 1 gwei
    
    # 가스비 = gas_limit * gas_price
    # gas_limit = 가스비 / gas_price
    gas_limits = gas_fees_wei / gwei_price
    
    print(f"🔢 평균 가스 사용량: {gas_limits.mean():.0f}")
    print(f"📈 최대 가스 사용량: {gas_limits.max():.0f}")
    print(f"📉 최소 가스 사용량: {gas_limits.min():.0f}")
    print(f"🎯 95% 안전 마진: {gas_limits.quantile(0.95):.0f}")
    
    # 권장 가스 한도 계산
    recommended_gas_limit = int(gas_limits.quantile(0.95) * 1.2)  # 20% 여유분
    
    print("\n🎯 권장 설정:")
    print("=" * 30)
    print(f"권장 가스 한도: {recommended_gas_limit:,}")
    print(f"권장 가스 가격: 1 gwei")
    print(f"예상 가스비: {recommended_gas_limit * gwei_price / 10**18:.8f} ETH")
    
    # 현재 설정과 비교
    current_gas = 60000
    current_price = 1 * 10**9  # 1 gwei
    current_cost = current_gas * current_price / 10**18
    
    print(f"\n🔄 현재 봇 설정 비교:")
    print(f"현재 가스 한도: {current_gas:,}")
    print(f"현재 가스비: {current_cost:.8f} ETH")
    
    if current_gas >= recommended_gas_limit:
        print("✅ 현재 설정이 충분합니다!")
    else:
        print("⚠️  현재 설정이 부족할 수 있습니다!")
    
    # 다양한 가스 가격별 비용 분석
    print(f"\n💡 다양한 가스 가격별 예상 비용:")
    for gwei in [0.5, 1, 2, 5]:
        cost = recommended_gas_limit * gwei * 10**9 / 10**18
        print(f"{gwei:3.1f} gwei: {cost:.8f} ETH (${cost * 3125:.4f})")  # ETH $3125 기준
    
    return {
        'recommended_gas_limit': recommended_gas_limit,
        'mean_gas_used': int(gas_limits.mean()),
        'max_gas_used': int(gas_limits.max()),
        'p95_gas_used': int(gas_limits.quantile(0.95))
    }

if __name__ == "__main__":
    result = analyze_gas_data() 